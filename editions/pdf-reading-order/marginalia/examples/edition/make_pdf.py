from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz
d=fitz.open()
for i,folio in enumerate(['iv','1','2']):
    p=d.new_page(width=432,height=540)
    p.insert_text((36,34),'Measurement bulletin',fontsize=9)
    p.insert_text((36,95),['Methods','Results','Appendix'][i],fontsize=19)
    p.insert_text((38,132),'See Figure 2 for temperature drift at heated chamber.',fontsize=11)
    p.insert_text((38,163),'The result [1] applies under steady conditions.',fontsize=11)
    if i==1:p.insert_text((38,242),'Figure 2: temperature drift at heated chamber.',fontsize=11)
    p.insert_text((38,475),'1. Independent calibration at heated chamber.',fontsize=8)
    p.insert_text((215,518),folio,fontsize=9)
d.set_toc([[1,'Methods',1],[1,'Results',2]])
d.save(Path(__file__).resolve().parent/'materials'/'paper.pdf')
