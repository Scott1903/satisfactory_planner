from model import create_model
from pyomo.environ import *

def optimize_production(data, resource_limits, inputs, outputs, recipes_off, weights, max_item):

    # Remove max_item from outputs if exists
    if max_item in outputs:
        del outputs[max_item]

    # Create model
    m = create_model(data, resource_limits, inputs, outputs, weights, max_item)

    # Turn off recipes given
    for recipe in recipes_off:
        m.r[recipe].fix(0)

    # Solve the model
    solver = SolverFactory('glpk', executable='E:\\Applications\\pyomo glpk\\glpk-4.65\\w64\\glpsol')
    result = solver.solve(m)
    
    # Collect results
    items_input = {data['items'][var_name]['name']: var.value for var_name, var in m.n.items() if var.value is not None and var.value > 0.001}
    items_output = {data['items'][var_name]['name']: var.value for var_name, var in m.x.items() if var.value is not None and var.value > 0.001}
    resources_needed = {data['resources'][var_name]['name']: var.value for var_name, var in m.i.items() if var.value is not None and var.value > 0.001 and var_name in resource_limits}
    items_needed = {data['items'][var_name]['name']: var.value for var_name, var in m.i.items() if var.value is not None and var.value > 0.001 and var_name not in resource_limits and var_name is not 'Power_Produced'}
    recipes_used = {data['recipes'][var_name]['name']: var.value for var_name, var in m.r.items() if var.value is not None and var.value > 0.001}
    power_produced = m.x['Power_Produced']()

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
        'items_input': items_input,
        'items_output': items_output,
        'resources_needed': resources_needed,
        'items_needed': items_needed,
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