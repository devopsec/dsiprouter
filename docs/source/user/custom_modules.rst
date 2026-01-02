Developing Custom Modules
================================    

Creating custom modules for dSIPRouter allows you to extend its functionality to meet specific needs. This guide provides an overview of how to create and integrate custom modules into the dSIPRouter framework.

1. Module Structure
--------------------
A custom module typically consists of the following components: 

- All modules should be placed into the [DSIPROUTER install directory]/`gui/modules/` directory.  For example, the numbers module is located at `gui/modules/numbers/`. 
- Each module should have its own subdirectory within the `modules` directory. This subdirectory will contain all the files related to that module, including routes, templates, static files, and database models.
- A typical module structure might look like this:
  
  ```
  gui/
  └── modules/
      └── your_module/
          ├── api/
          │   └── routes.py
          ├── templates/
          │   └── your_module_template.html
          ├── static/
          │   └── your_module_style.css
          ├── db/
          │   └── your_module_model.py
          └── __init__.py
  ```

  The api/routes.py file will define the routes for your module, while templates and static directories will hold the HTML and CSS files, respectively. The db directory will contain any database models needed for your module.

2. Module Initialization
-------------------------
The module should include an `__init__.py` file that contains an `init_module` function. This function will be called when the module is loaded, allowing you to register routes and perform any necessary setup.   
Example `__init__.py`:
```python
from flask import Blueprint
module_name = "your_module"
module_menu_name = "Your Module"
def init_module(app, csrf, settings):
    your_module_bp = Blueprint('your_module', __name__, template_folder='../templates', static_folder='static')
    
    @your_module_bp.route('/your_module')
    def your_module_home():
        return "Welcome to Your Module!"
    
    app.register_blueprint(your_module_bp)
```
Note in many cases, you want to define your routes in a separate file (e.g., `api/routes.py`) and import them into the `init_module` function. 

3. Define User Interface Elements
---------------------------------
If your module includes a user interface, you can define templates and static files within the module's

4. Define Database Models
---------------------------------
If your module requires database interaction, you can define your database models in the `db` directory

5. Loading the Module
------------------------
To load your custom module, you don't need to do anything special; the dSIPRouter application automatically scans the `modules` directory and loads any modules it finds. Ensure that your module follows the structure outlined above and includes the `init_module` function. 

6. Accessing Module Functionality
---------------------------------
Once your module is loaded, you can access its routes and functionality through the dSIPRouter web interface. The module will be added to the main navigation menu.  It uses the `module_menu_name` variable defined in the module to display the name in the menu. 