# image_loader.py
#
# Heroes are served from static/heroes/ via Streamlit static file serving
# (enableStaticServing in .streamlit/config.toml). A static URL is cached by
# the browser once; the previous base64-data-URI approach re-shipped ~300KB
# of image inside the HTML delta on every rerun, and the remote fallbacks
# (photodharma.net originals) were 4.5MB downloads per page view.
#
# Originals, kept for reference if the local files are ever regenerated:
#   nalanda_ruins    https://images.unsplash.com/photo-1582555172866-f73bb12a2ab3
#   rajgir           https://as1.ftcdn.net/jpg/00/86/33/28/1000_F_86332883_ZXujI7IQL8PtKEBILcFrJilWHSIjAWIa.jpg
#   pawapuri         https://www.holidify.com/images/attr_wiki/compressed/attr_wiki_2934.jpg
#   mithila_art      https://as2.ftcdn.net/v2/jpg/12/72/69/09/1000_F_1272690914_qcZgSMGEd5s4olAMYm5ELuWNLbw9L6wf.jpg
#   nalanda_monument https://photodharma.net/India/Nalanda/images/Nalanda-Original-00016.jpg
#   (default)        https://photodharma.net/India/Nalanda/images/Nalanda-Original-00004.jpg
import os

_HERO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "heroes")
_HEROES = {"nalanda_ruins", "rajgir", "pawapuri", "mithila_art", "nalanda_monument"}
_DEFAULT = "nalanda_default"


def hero_css_bg(image_name, width=None):
    name = image_name if image_name in _HEROES else _DEFAULT
    if not os.path.exists(os.path.join(_HERO_DIR, f"{name}.jpg")):
        name = _DEFAULT
    # "app/static/..." is the URL prefix Streamlit exposes static/ under.
    return f"url('app/static/heroes/{name}.jpg')"
