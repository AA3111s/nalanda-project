# image_loader.py
def hero_css_bg(image_name, width=None):
    urls = {
        "nalanda_ruins": "https://images.unsplash.com/photo-1582555172866-f73bb12a2ab3?q=80&w=2000&auto=format&fit=crop", 
        "rajgir": "https://as1.ftcdn.net/jpg/00/86/33/28/1000_F_86332883_ZXujI7IQL8PtKEBILcFrJilWHSIjAWIa.jpg?q=80&w=2000&auto=format&fit=crop",
        "pawapuri": "https://www.holidify.com/images/attr_wiki/compressed/attr_wiki_2934.jpg?q=80&w=2000&auto=format&fit=crop",
        # New Additions for the Carousel
        "mithila_art": "https://as2.ftcdn.net/v2/jpg/12/72/69/09/1000_F_1272690914_qcZgSMGEd5s4olAMYm5ELuWNLbw9L6wf.jpg?q=80&w=2000&auto=format&fit=crop", # Placeholder for Madhubani/Mithila art
        "nalanda_monument": "https://photodharma.net/India/Nalanda/images/Nalanda-Original-00016.jpg?q=80&w=2000&auto=format&fit=crop" # Alternative Nalanda/Bihar monument view
    }
    
    default_url = "https://photodharma.net/India/Nalanda/images/Nalanda-Original-00004.jpg?q=80&w=2000&auto=format&fit=crop"
    img_url = urls.get(image_name, default_url)
    return f"url('{img_url}')"
