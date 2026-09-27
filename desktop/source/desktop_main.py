"""Native launcher target, also usable by developers without the JSON harness."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lertx.desktop_entry import main
raise SystemExit(main())
