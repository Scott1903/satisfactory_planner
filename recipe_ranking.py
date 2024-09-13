import json
from pyomo.environ import *
import pandas as pd
from model import create_model
from pyomo.environ import *


# -------------------------------------------- Data --------------------------------------------
# Load data from data.json
data_file = 'Data\data.json'
try:
    with open(data_file, 'r') as file:
        data = json.load(file)
except Exception as e:
    data = None

resource_limits = {
            'Desc_Water_C': 100000,
            'Desc_OreGold_C': 15000,
            'Desc_RawQuartz_C': 13500,
            'Desc_Coal_C': 42300,
            'Desc_NitrogenGas_C': 12000,
            'Desc_OreIron_C': 92100,
            'Desc_Sulfur_C': 10800,
            'Desc_OreBauxite_C': 12300,
            'Desc_OreUranium_C': 2100,
            'Desc_Stone_C': 69900,
            'Desc_LiquidOil_C': 12600,
            'Desc_OreCopper_C': 36900,
            'Desc_SAM_C': 10200}

inputs = {}

outputs = {
    'Desc_SpaceElevatorPart_9_C': 10,
    'Desc_SpaceElevatorPart_10_C': 10,
    'Desc_SpaceElevatorPart_12_C': 2.56,
    'Desc_SpaceElevatorPart_11_C': 2,
    'Desc_CrystalShard_C': 5,
    'Desc_PackagedIonizedFuel_C': 100,
    'Desc_FluidCanister_C': 100,
    'Desc_HazmatFilter_C': 2,
    'Desc_NobeliskNuke_C': 2,
    'Desc_CartridgeChaos_C': 50,
    'Desc_IronRod_C': 600,
    'Desc_Cable_C': 200,
    'Desc_IronScrew_C': 2000}

weights = {
    'Power Use': 0.0,
    'Item Use': 0.4,
    'Building Use': 0,
    'Resource Use': 0,
    'Buildings Scaled': 30,
    'Resources Scaled': 1,
    'Uranium Waste': 9999999}

max_item = False
# Remove max_item from outputs if exists
if max_item in outputs:
    del outputs[max_item]

recipes_off = []


# -------------------------------------------- Model --------------------------------------------
m = create_model(data, resource_limits, inputs, outputs, weights, max_item)

# Turn off recipes given
for recipe in recipes_off:
    m.r[recipe].fix(0)

# Solve the model
solver = SolverFactory('glpk', executable='E:\\Applications\\pyomo glpk\\glpk-4.65\\w64\\glpsol')

m.c.add(expr = m.x['Power_Produced_Fuel'] == m.power_use/2)
m.c.add(expr = m.x['Power_Produced_Nuclear'] == m.power_use/2)


# -------------------------------------------- Ranking --------------------------------------------

# Create dict of recipe alternates for each item
recipes_dict = {}
for recipe_key, recipe_data in data['recipes'].items():
    if len(recipe_data['products']) > 0:
        for product in recipe_data['products']:
            product_item = product['item']
            recipes_dict[product_item] = recipes_dict.get(product_item, []) + [recipe_key]

# Modify recipes list for specific items:
recipes_dict['Desc_HeavyOilResidue_C'] = [
        recipe for recipe in recipes_dict['Desc_HeavyOilResidue_C']
        if recipe not in ['Recipe_Plastic_C', 'Recipe_Rubber_C']
    ]

# Initialize an empty list to store the results
results_list = []

all_items = {**data['resources'], **data['items']}
# Test Alternates
for item, recipes in recipes_dict.items():
    if item in all_items.keys():
        print(item)
        for recipe_key in recipes:
            # Create a copy of the model
            t = m.clone()
            for recipe_key2 in recipes:
                if recipe_key != recipe_key2 \
                        or (item == 'Desc_PolymerResin_C' and recipe_key == 'Recipe_Alternate_HeavyOilResidue_C' and recipe_key2 == 'Recipe_Alternate_HeavyOilResidue_C') \
                        or (item == 'Desc_HeavyOilResidue_C' and recipe_key == 'Recipe_Alternate_PolymerResin_C' and recipe_key2 == 'Recipe_Alternate_PolymerResin_C'): # Test cases when both recipes are not used to compare to on sheet
                    t.c.add(expr = t.r[recipe_key2] == 0)
            # Run model on new constraints
            result = solver.solve(t)
            if result.solver.termination_condition == TerminationCondition.optimal:
                result_dict = {
                    'Item': all_items[item]['name'],
                    'Recipe': data['recipes'][recipe_key]['name'],
                    'Power': round(t.power_use(), 1),
                    'Items': round(t.item_use(), 1),
                    'Buildings': round(t.building_use(), 1),
                    'Resources': round(t.resource_use(), 1),
                    'Buildings Scaled': round(t.buildings_scaled(), 1),
                    'Resources Scaled': round(t.resources_scaled(), 1)
                }
                for item_key, item_var in t.i.items():
                    if item_key in data['resources'].keys():
                        result_dict[data['resources'][item_key]['name']] = round(item_var.value, 1)
                results_list.append(result_dict)

# Convert the list of dictionaries into a DataFrame
results_df = pd.DataFrame(results_list)
print(results_df)

# Save df to .csv
results_df.to_csv('results.csv', index=False)