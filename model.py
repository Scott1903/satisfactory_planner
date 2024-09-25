from pyomo.environ import *
import math

def extract_items(data):
    resources = set(data['resources'].keys())
    recipes = set(data['recipes'].keys())
    products = set()
    ingredients = set()

    for recipe_key, recipe_data in data['recipes'].items():
        products.update(p['item'] for p in recipe_data['products'] if p['item'] not in resources)
        ingredients.update(i['item'] for i in recipe_data['ingredients'] if i['item'] not in resources)

    return resources, recipes, products, ingredients

def define_variables(m, all_items, recipes):
    m.n = Var(all_items, within=NonNegativeReals)  # Input Items
    m.x = Var(all_items, within=NonNegativeReals)  # Output Items
    m.i = Var(all_items, within=NonNegativeReals)  # Intermediate items
    m.r = Var(recipes, within=NonNegativeReals)  # Amount of each recipe used

    # Variables for objective cost
    m.power_use = Var(within=NonNegativeReals)
    m.item_use = Var(within=NonNegativeReals)
    m.building_use = Var(within=NonNegativeReals)
    m.resource_use = Var(within=NonNegativeReals)
    m.buildings_scaled = Var(within=NonNegativeReals)
    m.resources_scaled = Var(within=NonNegativeReals)
    m.sink_points = Var(within=NonNegativeReals)

def fix_input_amounts(m, settings, all_items):
    for item in all_items:
        if item in settings['inputs'].keys():
            m.n[item].fix(settings['inputs'][item])
        else:
            m.n[item].fix(0)

def fix_output_amounts(m, settings):
    if settings['outputs'] == []:
        return
    for item, amount in settings['outputs'].items():
        if item in m.x:
            m.x[item].fix(amount)
        else:
            raise KeyError(f"Output item '{item}' not found in model items.")

def add_product_constraints(m, products, data):
    for item in products:
        expr = m.n[item] + sum(
            p['amount'] * 60 / recipe_data['time'] * m.r[recipe_key]
            for recipe_key, recipe_data in data['recipes'].items()
            for p in recipe_data['products']
            if p['item'] == item)
        if item in m.i:
            m.c.add(expr == m.i[item])
        else:
            raise KeyError(f"Item '{item}' not found in model intermediate items.")

def add_ingredient_constraints(m, ingredients, data):
    for item in ingredients:
        expr = m.x[item] + sum(
            p['amount'] * 60 / recipe_data['time'] * m.r[recipe_key]
            for recipe_key, recipe_data in data['recipes'].items()
            for p in recipe_data['ingredients']
            if p['item'] == item)
        if item in m.i:
            m.c.add(expr == m.i[item])
        else:
            raise KeyError(f"Item '{item}' not found in model intermediate items.")

def add_resource_constraints(m, settings):
    for resource, limit in settings['resource_limits'].items():
        if resource in m.i:
            m.c.add(m.i[resource] <= limit)
        else:
            raise KeyError(f"Resource '{resource}' not found in model items.")

def calculate_power_use(m, data, recipes):
    expr = sum(data['recipes'][recipe_key]['power_use'] * m.r[recipe_key] for recipe_key in recipes) + sum(m.i[item] * 0.168 for item in m.i if item in data['resources'])
    m.c.add(expr == m.power_use)

def calculate_item_use(m, items):
    expr = sum(m.i[item] for item in items if item != 'Power_Produced' and item != 'Power_Produced_Other' and item != 'Power_Produced_Fuel' and item != 'Power_Produced_Nuclear')
    m.c.add(expr == m.item_use)

def calculate_building_use(m, recipes):
    expr = sum(m.r[recipe_key] for recipe_key in recipes)
    m.c.add(expr == m.building_use)

def calculate_resource_use(m, settings):
    expr = sum(m.i[item] for item in settings['resource_limits'])
    m.c.add(expr == m.resource_use)

def calculate_buildings_scaled(m, data, recipes):
    expr = sum((len(data['recipes'][recipe_key]['ingredients']) + len(data['recipes'][recipe_key]['products']) - 1) ** 1.584963 * m.r[recipe_key]/3 for recipe_key in recipes)
    m.c.add(expr == m.buildings_scaled)

def calculate_resources_scaled(m, resource_weights):
    expr = sum(resource_weights[resource] * m.i[resource] for resource in resource_weights if resource in m.i)
    m.c.add(expr == m.resources_scaled)

def calculate_sink_points(m, data, items):
    expr = sum(data['items'][item]['points'] * m.x[item] for item in items if item in data['items'] and data['items'][item]['points'] > 0 and data['items'][item]['form'] == 'RF_SOLID')
    m.c.add(expr == m.sink_points)

def set_objective(m, settings):
    waste_penalty_expr = m.x['Desc_NuclearWaste_C'] + \
                         m.x['Desc_NonFissibleUranium_C'] + \
                         m.x['Desc_PlutoniumPellet_C'] + \
                         m.x['Desc_PlutoniumCell_C'] + \
                         m.x['Desc_PlutoniumWaste_C'] + \
                         m.x['Desc_Ficsonium_C']
    
    if settings['checkbox_Nuclear Waste']:
        waste_penalty_expr = waste_penalty_expr + m.x['Desc_PlutoniumFuelRod_C']/10
    
    if settings['max_item'] == 'Points':
        # Set Limited Resources to Zero
        m.i['Desc_AlienProtein_C'].fix(0)
        m.i['Desc_Gift_C'].fix(0)
        m.i['Desc_Wood_C'].fix(0)
        m.i['Desc_StingerParts_C'].fix(0)
        m.i['Desc_SpitterParts_C'].fix(0)
        m.i['Desc_HogParts_C'].fix(0)
        m.i['Desc_HatcherParts_C'].fix(0)
        m.i['Desc_Mycelia_C'].fix(0)
        m.i['Desc_Leaves_C'].fix(0)
        m.objective = Objective(
            expr = m.power_use * settings['weights']['Power Use'] + waste_penalty_expr * settings['weights']['Nuclear Waste'] - m.sink_points,
            sense = minimize)
        
    elif settings['max_item']:
        m.objective = Objective(
            expr = m.power_use * settings['weights']['Power Use'] + waste_penalty_expr * settings['weights']['Nuclear Waste'] - m.x[settings['max_item']] * 99999,
            sense = minimize)
        
    else:
        m.objective = Objective(
            expr = m.power_use * settings['weights']['Power Use'] + \
                m.item_use * settings['weights']['Item Use'] + \
                m.building_use * settings['weights']['Building Use'] + \
                m.resource_use * settings['weights']['Resource Use'] + \
                m.buildings_scaled * settings['weights']['Buildings Scaled'] + \
                m.resources_scaled * settings['weights']['Resources Scaled'] + \
                waste_penalty_expr * settings['weights']['Nuclear Waste'],
            sense = minimize)

def create_model(data, settings):
    m = ConcreteModel()
    m.c = ConstraintList()

    resources, recipes, products, ingredients = extract_items(data)
    define_variables(m, resources.union(products, ingredients), recipes)
    fix_input_amounts(m, settings, resources.union(products, ingredients))
    fix_output_amounts(m, settings)
    add_product_constraints(m, products, data)
    add_ingredient_constraints(m, resources.union(products, ingredients), data)
    add_resource_constraints(m, settings)
    
    filtered_limits = {key: value for key, value in settings['resource_limits'].items() if key != 'Desc_Water_C'}
    avg_limit = sum(filtered_limits.values()) / len(filtered_limits)
    resource_weights = {}
    for resource in resources:
        resource_weights[resource] = avg_limit / settings['resource_limits'][resource]

    calculate_power_use(m, data, recipes)
    calculate_item_use(m, resources.union(products, ingredients))
    calculate_building_use(m, recipes)
    calculate_resource_use(m, settings)
    calculate_buildings_scaled(m, data, recipes)
    calculate_resources_scaled(m, resource_weights)
    calculate_sink_points(m, data, products)
    set_objective(m, settings)

    return m
