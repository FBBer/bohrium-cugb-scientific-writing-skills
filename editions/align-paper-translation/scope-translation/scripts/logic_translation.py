"""Make a bilingual edition and review changes to logical scope and strength."""
import re
from edition_io import main,anchor,require
from sourcebook import dump,h,html_page,html_table,link
RULES=[
 ("not-all",r"\bnot (?:all|every)\b",r"并非(?:每|全部|所有)|不全是|并不都|未必都",r"全部(?:都)?不|均不|无一","部分否定"),
 ("only-if",r"\bonly if\b",r"只有.{0,90}(?:才|方)|仅当|为.{0,15}必要条件",r"只要.{0,45}就","必要条件"),
 ("unless",r"\bunless\b",r"除非|除.{0,25}外|若不|如果不",r"$^","除外条件"),
 ("nonsignificant",r"\b(?:no (?:statistically )?significant (?:difference|effect)|not (?:statistically )?significant)\b",r"差异不显著|无显著|未(?:见|发现|观察到)显著|统计.{0,8}不显著|不具有统计学意义",r"完全相同|毫无作用|没有任何影响","统计显著性"),
 ("possible",r"\b(?:may|might|possibly)\b",r"可能|或许|也许|有可能|或可",r"必然|一定会","可能性"),
 ("at-most",r"\bat most\b",r"至多|最多|不超过|≤",r"至少|不少于|≥","上界")]
def render(sources,spec,out):
    refs=[];rows=[];audit=[];ids=set()
    for sec in spec["sections"]:
        for seg in sec["segments"]:
            ident=seg["id"];require(ident not in ids,"duplicate segment "+ident);ids.add(ident)
            a=anchor(sources,seg["evidence"]);translation=seg["translation"]
            require(translation.strip(),"empty translation")
            flags=[]
            for code,src,good,bad,label in RULES:
                if re.search(src,a["quote"],re.I) and (re.search(bad,translation) or not re.search(good,translation)):
                    flags.append({"code":code,"feature":label,"source":a["quote"],"translation":translation})
            audit.extend(dict(segment=ident,**f) for f in flags)
            refs.append(a);rows.append(dict(id=ident,section=sec["heading"],source=a,translation=translation,review=flags))
    require(rows,"no passages")
    body=[]
    for sec in spec["sections"]:
        selected=[v for v in rows if v["section"]==sec["heading"]]
        body.append("<h2>"+h(sec["heading"])+"</h2>"+html_table(("原文","译文"),[(h(v["source"]["quote"])+" "+link(v["source"]),h(v["translation"])) for v in selected]))
    if audit:body.append("<h2>需回读的译句</h2>"+"".join("<p>"+h(a["segment"]+" · "+a["feature"]+"　"+a["translation"])+"</p>" for a in audit))
    html_page(out/"translation.html",spec["title"],"".join(body),refs)
    dump(out/"translation.json",dict(author="GPT-6.2Astra",segments=rows,review=audit))
    (out/"translation.txt").write_text("\n\n".join(v["translation"] for v in rows)+"\n",encoding="utf-8")
if __name__=="__main__":main(render)
