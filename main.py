from model import create_model
import os
from pyomo.environ import *

def optimize_production(data, settings):
    # Remove max_item from outputs if exists
    if settings['max_item'] in settings['outputs']:
        del settings['outputs'][settings['max_item']]

    # Create model
    m = create_model(data, settings)

    # Turn off recipes given
    for recipe in settings['recipes_off']:
        m.r[recipe].fix(0)

    # Solve the model
    solver = SolverFactory('glpk', executable=os.path.join(os.getenv('GLPK_PATH'), 'glpsol.exe'))
    result = solver.solve(m)
    
    # Collect results
    sink_points = m.sink_points()
    items_input = {data['items'][var_name]['name']: var.value for var_name, var in m.n.items() if var.value is not None and var.value > 0.001}
    items_output = {data['items'][var_name]['name']: var.value for var_name, var in m.x.items() if var.value is not None and var.value > 0.001}
    resources_needed = {data['resources'][var_name]['name']: var.value for var_name, var in m.i.items() if var.value is not None and var.value > 0.001 and var_name in settings['resource_limits']}
    items_needed = {data['items'][var_name]['name']: var.value for var_name, var in m.i.items() if var.value is not None and var.value > 0.001 and var_name not in settings['resource_limits']}
    items_not_needed = {var_name: var.value for var_name, var in m.i.items() if var.value is not None and var.value <= 0.001 and var_name not in settings['resource_limits']}
    recipes_used = {data['recipes'][var_name]['name']: var.value for var_name, var in m.r.items() if var.value is not None and var.value > 0.001}
    power_produced = m.x['Power_Produced_Other']() + m.x['Power_Produced_Fuel']() + m.x['Power_Produced_Nuclear']()

    products_map = {
    data['items'][item]['name'] if item in data['items'] else data['resources'][item]['name']: {
        data['recipes'][recipe]['name']: (60 / data['recipes'][recipe]['time']) * ingredient['amount'] * recipe_val.value
        for recipe, recipe_val in m.r.items()
        if recipe_val.value is not None and recipe_val.value > 0.001
        for ingredient in data['recipes'][recipe]['ingredients']
        if item == ingredient['item']}
    for item, item_val in m.i.items()
    if item_val.value is not None and item_val.value > 0.001}

    all_items = {**data['items'], **data['resources']}
    ingredients_map = {
    data['recipes'][recipe]['name']: {
        all_items[ingredient['item']]['name']: (60 / data['recipes'][recipe]['time']) * ingredient['amount'] * recipe_val.value
        for ingredient in data['recipes'][recipe]['ingredients']}
    for recipe, recipe_val in m.r.items()
    if recipe_val.value is not None and recipe_val.value > 0.001}

    # Extract costs
    power_use = m.power_use()
    item_use = m.item_use()
    buildings = m.building_use()
    resources = m.resource_use()
    buildings_scaled = m.buildings_scaled()
    resources_scaled = m.resources_scaled()

    return {
        'sink_points': sink_points,
        'items_input': items_input,
        'items_output': items_output,
        'resources_needed': resources_needed,
        'items_needed': items_needed,
        'items_not_needed': items_not_needed,
        'recipes_used': recipes_used,
        'power_produced': power_produced,
        'power_use': power_use,
        'item_use': item_use,
        'buildings': buildings,
        'resources': resources,
        'buildings_scaled': buildings_scaled,
        'resources_scaled': resources_scaled,
        'products_map': products_map,
        'ingredients_map': ingredients_map}