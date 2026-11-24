"""Run the edition on a folder of actual materials and an optional author's plan."""
import argparse
import json
from pathlib import Path
from sourcebook import Sources, dump, exact_rows, table
from edition_work import produce

def main():
    cfg=json.loads(Path(__file__).with_name('edition.json').read_text(encoding='utf-8'))
    ap=argparse.ArgumentParser(description=cfg['title'])
    ap.add_argument('materials',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--plan',type=Path,help='JSON with cited rows and edition-specific options')
    ap.add_argument('--index',action='store_true',help='write searchable source passages and stop')
    args=ap.parse_args()
    if not args.materials.is_dir(): ap.error('materials directory does not exist')
    dest=args.output.resolve()
    if dest==args.materials.resolve() or dest.is_relative_to(args.materials.resolve()):
        ap.error('put output outside the source directory')
    dest.mkdir(parents=True,exist_ok=True)
    sources=Sources(args.materials)
    table(dest/'source-index.tsv',('source','loc','text'),([r['source'],r['loc'],r['text']] for r in sources.rows))
    if args.index: return 0
    plan=json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else {}
    rows,issues=exact_rows(sources,plan.get('rows',[]))
    if cfg.get('requires_plan') and not rows:
        issues.append({'reason':'This edition needs cited rows. Use source-index.tsv and the example plan to prepare them.'})
    errors=list(sources.notes)+issues
    outputs=[]
    if sources.rows and (rows or not cfg.get('requires_plan')):
        try: outputs=produce(cfg['mode'],sources,rows,plan,dest,cfg['title'])
        except (ValueError,KeyError,TypeError,ArithmeticError,IndexError) as e:
            errors.append({'reason':str(e)})
    if not sources.rows: errors.append({'reason':'No readable source passages.'})
    status='partial' if outputs and errors else 'complete' if outputs else 'insufficient'
    dump(dest/'edition-report.json',{'edition':cfg['mode'],'status':status,'artifacts':outputs,'passages':len(sources.rows),'sources':len({r['source'] for r in sources.rows}),'cited_rows':len(rows),'issues':errors})
    return 0 if outputs else 2
if __name__=='__main__': raise SystemExit(main())
