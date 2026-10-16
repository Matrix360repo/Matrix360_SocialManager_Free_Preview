"""Generate review-only PNG samples with verified Lakhotia facts.

Run: python tools/build_brand_previews.py
No model/API credentials, contact lists or live publishing required.
"""
from pathlib import Path
from brand_renderer_v14 import render_card_v14

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"artifacts"/"brand_previews"
SAFE_CAPTION=("Lakhotia Industrial Complex, Ranihati–Amta Road, Howrah. "
              "1,000 bighas under development; 2,500+ bighas planned expansion. "
              "Approximately 4 km from NH-16. +91 74500 08999 "
              "www.lakhotiaindustrialcomplex.com")
EXAMPLES=(
    ("Industrial opportunity", "Land planned for business growth", 
     "Discuss your industrial land requirement"),
    ("Planning framework", "Plan your next industrial expansion", 
     "Request a consultation"),
    ("Expert consultation", "Expert guidance for your industrial move",
     "Speak with our team"),
)
def main():
    DEST.mkdir(parents=True,exist_ok=True)
    for idx,(pillar,headline,cta) in enumerate(EXAMPLES):
        candidate={"option":idx+1,"pillar":pillar,"headline":headline,
                   "subheadline":"Industrial land planning in Howrah",
                   "caption":SAFE_CAPTION,"cta":cta}
        target=DEST/f"lakhotia_v14_family_{idx+1}.png"
        render_card_v14(candidate,target,idx)
        print(f"CREATED {target.relative_to(ROOT)} ({target.stat().st_size:,} bytes)")
if __name__=="__main__":main()
