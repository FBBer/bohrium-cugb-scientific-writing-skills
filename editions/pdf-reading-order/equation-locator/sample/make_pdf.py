"""Make an original two-page plate-calibration example."""
from pathlib import Path
import sys
import pymupdf as fitz
def create(path,duplicate=False):
    with fitz.open() as d:
        one=d.new_page()
        one.insert_text((58,70),"Plate calibration")
        one.insert_text((58,110),"The displacement follows Eq. (2).")
        one.insert_text((58,140),"Compare Eq. (9) for the missing reference.")
        two=d.new_page()
        two.insert_text((112,160),"u = a + b t")
        two.insert_text((492,160),"(2)")
        if duplicate:
            two.insert_text((112,230),"v = c + t")
            two.insert_text((492,230),"(2)")
        d.save(path)
if __name__=="__main__":create(Path(sys.argv[1]),"--duplicate" in sys.argv)
