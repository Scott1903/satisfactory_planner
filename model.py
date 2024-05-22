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
    m.x = Var(all_items, within=NonNegativeReals)  # Final production of items
    m.i = Var(all_items, within=NonNegativeReals)  # Intermediate items
    m.r = Var(recipes, within=NonNegativeReals)  # Amount of each recipe used

    # Variables for objective cost
    m.power_use = Var(within=NonNegativeReals)
    m.item_use = Var(within=NonNegativeReals)
    m.building_use = Var(within=NonNegativeReals)
    m.resource_use = Var(within=NonNegativeReals)
    m.buildings_scaled = Var(within=NonNegativeReals)
    m.resources_scaled = Var(within=NonNegativeReals)

def fix_output_amounts(m, outputs):
    if outputs == []:
        return
    for item, amount in outputs.items():
        if item in m.x:
            m.x[item].fix(amount)
        else:
            raise KeyError(f"Output item '{item}' not found in model items.")

def add_product_constraints(m, products, data):
    for item in products:
        expr = sum(
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

def add_resource_constraints(m, resource_limits):
    for resource, limit in resource_limits.items():
        if resource in m.i:
            m.c.add(m.i[resource] <= limit)
        else:
            raise KeyError(f"Resource '{resource}' not found in model items.")

def calculate_power_use(m, data, recipes):
    expr = sum(data['machines'][data['recipes'][recipe_key]['machine']]['power_use'] * m.r[recipe_key] for recipe_key in recipes) + sum(m.i[item] * 0.167 for item in m.i if item in data['resources'])
    m.c.add(expr == m.power_use)

def calculate_item_use(m, items):
    expr = sum(m.i[item] for item in items if item != 'Power_Produced')
    m.c.add(expr == m.item_use)

def calculate_building_use(m, recipes):
    expr = sum(m.r[recipe_key] for recipe_key in recipes)
    m.c.add(expr == m.building_use)

def calculate_resource_use(m, resource_limits):
    expr = sum(m.i[item] for item in resource_limits)
    m.c.add(expr == m.resource_use)

def calculate_buildings_scaled(m, data, recipes):
    expr = sum((len(data['recipes'][recipe_key]['ingredients']) + len(data['recipes'][recipe_key]['products']) - 1) ** 2 * m.r[recipe_key] * 4.1 for recipe_key in recipes)
    m.c.add(expr == m.buildings_scaled)

def calculate_resources_scaled(m, data, resource_weights):
    expr = sum(resource_weights[resource] * m.i[resource] for resource in resource_weights if resource in m.i)
    m.c.add(expr == m.resources_scaled)

def set_objective(m, weights, max_item):
    if max_item:
        max_item_expr = -(m.x[max_item] * 9999999)
    else:
        max_item_expr = 0

    waste_penalty_expr = m.x['Desc_NuclearWaste_C'] + \
                         m.x['Desc_NonFissibleUranium_C'] + \
                         m.x['Desc_PlutoniumPellet_C'] + \
                         m.x['Desc_PlutoniumCell_C']

    m.objective = Objective(
        expr = m.power_use * weights['Power Use'] + \
               m.item_use * weights['Item Use'] + \
               m.building_use * weights['Building Use'] + \
               m.resource_use * weights['Resource Use'] + \
               m.buildings_scaled * weights['Buildings Scaled'] + \
               m.resources_scaled * weights['Resources Scaled'] + \
               waste_penalty_expr * weights['Uranium Waste'] + \
               max_item_expr,
        sense = minimize)

def create_model(data, resource_limits, outputs, weights, max_item):
    m = ConcreteModel()
    m.c = ConstraintList()

    resources, recipes, products, ingredients = extract_items(data)
    define_variables(m, resources.union(products, ingredients), recipes)
    fix_output_amounts(m, outputs)
    add_product_constraints(m, products, data)
    add_ingredient_constraints(m, resources.union(products, ingredients), data)
    add_resource_constraints(m, resource_limits)
    
    filtered_limits = {key: value for key, value in resource_limits.items() if key != 'Desc_Water_C'}
    avg_limit = sum(filtered_limits.values()) / len(filtered_limits)
    resource_weights = {}
    for resource in resources:
        resource_weights[resource] = avg_limit / resource_limits[resource]

    calculate_power_use(m, data, recipes)
    calculate_item_use(m, resources.union(products, ingredients))
    calculate_building_use(m, recipes)
    calculate_resource_use(m, resource_limits)
    calculate_buildings_scaled(m, data, recipes)
    calculate_resources_scaled(m, data, resource_weights)
    set_objective(m, weights, max_item)

    return m
