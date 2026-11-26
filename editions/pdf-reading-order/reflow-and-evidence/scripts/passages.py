"""Find quoted PDF text and restore candidate word continuations at page turns."""
import argparse
import json
import re
import unicodedata
from pathlib import Path

def normalized(text):
    return " ".join(unicodedata.normalize("NFKC",text).replace("\u00ad","-").split()).casefold()

def anchor(page, line):
    return {"page":page["page"],"line":line["id"],"bbox":line["bbox"],"text":line["text"]}

def cross_page_pairs(pages):
    pairs=[]
    for first,second in zip(pages,pages[1:]):
        if not first["lines"] or not second["lines"]:
            continue
        left,right=first["lines"][-1],second["lines"][0]
        if left["role"]!="body" or right["role"]!="body":
            continue
        if left["bbox"][1]<first["size"][1]*.60 or right["bbox"][3]>second["size"][1]*.35:
            continue
        tail=left["text"].rstrip();head=right["text"].lstrip()
        if not re.search(r"[^\W\d_][\-\u00ad‐]$",tail) or not re.match(r"[a-zà-öø-ÿ]",head):
            continue
        al,ar=anchor(first,left),anchor(second,right)
        pairs.append({"anchors":[al,ar],"spellings":[tail[:-1]+head,tail+head],
                      "basis":"Lowercase continuation following a printed line-end hyphen; both spellings retained."})
    return pairs

def lookup(layout, phrase):
    q=normalized(phrase)
    if not q:raise ValueError("Use a non-empty passage")
    hits=[]
    for page in layout["pages"]:
        for line in page["lines"]:
            if q in normalized(line.get("display_text",line["text"])) or q in normalized(line["text"]):
                hits.append({"anchors":[anchor(page,line)],"form":"literal"})
    for pair in cross_page_pairs(layout["pages"]):
        left=pair["anchors"][0]["text"].rstrip()
        for label,value,boundary in zip(("rejoined","hyphenated"),pair["spellings"],(len(normalized(left[:-1])),len(normalized(left)))):
            text=normalized(value)
            if any(m.start()<boundary<m.end() for m in re.finditer(re.escape(q),text)):
                hits.append({"anchors":pair["anchors"],"form":label})
                break
    return hits

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout",type=Path);parser.add_argument("phrase")
    args=parser.parse_args()
    print(json.dumps(lookup(json.loads(args.layout.read_text()),args.phrase),ensure_ascii=False,indent=2))
