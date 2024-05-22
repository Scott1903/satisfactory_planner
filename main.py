from model import create_model
from pyomo.environ import *

def optimize_production(data, resource_limits, outputs, recipes_off, weights, max_item):

    # Remove max_item from outputs if exists
    if max_item in outputs:
        del outputs[max_item]

    # Create model
    m = create_model(data, resource_limits, outputs, weights, max_item)

    # Turn off recipes given
    for recipe in recipes_off:
        m.r[recipe].fix(0)

    # Solve the model
    solver = SolverFactory('glpk', executable='E:\\Applications\\pyomo glpk\\glpk-4.65\\w64\\glpsol')
    result = solver.solve(m)
    
    # Collect results
    items_output = {data['items'][var_name]['name']: var.value for var_name, var in m.x.items() if var.value is not None and var.value > 0.001}
    resources_needed = {data['resources'][var_name]['name']: var.value for var_name, var in m.i.items() if var.value is not None and var.value > 0.001 and var_name in resource_limits}
    items_needed = {data['items'][var_name]['name']: var.value for var_name, var in m.i.items() if var.value is not None and var.value > 0.001 and var_name not in resource_limits and var_name is not 'Power_Produced'}
    recipes_used = {data['recipes'][var_name]['name']: var.value for var_name, var in m.r.items() if var.value is not None and var.value > 0.001}
    power_produced = m.x['Power_Produced']()

    # Extract costs
    power_use = m.power_use()
    item_use = m.item_use()
    buildings = m.building_use()
    resources = m.resource_use()
    buildings_scaled = m.buildings_scaled()
    resources_scaled = m.resources_scaled()

    return {
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
        'resources_scaled': resources_scaled}