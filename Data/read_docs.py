import json
import re

# Strings for relevant class types in Docs.json
ITEM_CLASSES = [
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptor'",
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptorNuclearFuel'",
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGItemDescriptorBiomass'"]
RESOURCE_CLASS = "/Script/CoreUObject.Class'/Script/FactoryGame.FGResourceDescriptor'"
MACHINE_CLASSES = [
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturer'"]
VARIABLE_MACHINE_CLASSES = [
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturerVariablePower'"]
GENERATOR_CLASSES = [
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableGeneratorFuel'",
    "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableGeneratorNuclear'"]
RECIPE_CLASS = "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'"

def read_docs(file_path):
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            docs_data = json.load(file)
    except Exception as e:
        print(f"Failed to load file: {e}")
        return {}

    data_dict = {
        'items': {},
        'resources': {},
        'recipes': {},
        'machines': {},
        'generators': {}}

    for entry in docs_data:
        native_class = entry['NativeClass']

        if native_class in ITEM_CLASSES:
            load_items(entry['Classes'], data_dict['items'])
        elif native_class == RESOURCE_CLASS:
            load_items(entry['Classes'], data_dict['resources'])
        elif native_class in MACHINE_CLASSES:
            load_machines(entry['Classes'], data_dict['machines'])
        elif native_class in VARIABLE_MACHINE_CLASSES:
            load_variable_machines(entry['Classes'], data_dict['machines'])

    data_dict['items'].update({'Power_Produced': {'name': 'Power', 'points': 0.0}})
    all_items = {**data_dict['items'], **data_dict['resources']}
    
    for entry in docs_data:
        native_class = entry['NativeClass']
        if native_class == RECIPE_CLASS:
            load_recipes(entry['Classes'], data_dict['recipes'], all_items, data_dict['machines'])
        elif native_class in GENERATOR_CLASSES:
            load_generators(entry['Classes'], data_dict['machines'], data_dict['recipes'], all_items)

    with open('data.json', 'w') as json_file:
        json.dump(data_dict, json_file, indent=4)

    print(f'Data successfully written to data.json')

def load_items(classes, items):
    for data in classes:
        energy_value = float(data['mEnergyValue'])
        if data['mForm'] in ['RF_LIQUID', 'RF_GAS']:
            energy_value *= 1000
        items[data['ClassName']] = {
            'name': data['mDisplayName'],
            'energy': energy_value,
            'form': data['mForm'],
            'points': int(data['mResourceSinkPoints'])}

def load_recipes(classes, recipes, all_items, machines):
    for data in classes:
        machine = re.search(r'Build_([\w]+)_C', data['mProducedIn'])
        if machine:
            recipes[data['ClassName']] = {
                'name': data['mDisplayName'],
                'time': float(data['mManufactoringDuration']),
                'ingredients': extract_products(data['mIngredients'], all_items),
                'products': extract_products(data['mProduct'], all_items),
                'machine': f"Build_{machine.group(1)}_C",
                'power_use': machines[f"Build_{machine.group(1)}_C"]['power_use']}
            if float(data['mVariablePowerConsumptionConstant']) > 0:
                recipes[data['ClassName']]['power_use'] = float(data['mVariablePowerConsumptionConstant']) + float(data['mVariablePowerConsumptionFactor'])/2

def extract_products(data, all_items):
    products = []
    for match in re.findall(r'Desc_([\w]+)_C.*?Amount=([\d]+)', data):
        item_name = f"Desc_{match[0]}_C"
        amount = int(match[1])
        if all_items.get(item_name, {}).get('form') in ['RF_LIQUID', 'RF_GAS']:
            amount /= 1000
        products.append({'item': item_name, 'amount': amount})
    return products

def load_machines(classes, machines):
    for data in classes:
        machines[data['ClassName']] = {
            'name': data['mDisplayName'],
            'power_use': float(data['mPowerConsumption']),
            'power_produced': 0}

def load_variable_machines(classes, machines):
    for data in classes:
        machines[data['ClassName']] = {
            'name': data['mDisplayName'],
            'power_use': (float(data['mEstimatedMaximumPowerConsumption']) - float(data['mEstimatedMininumPowerConsumption'])) / 2 + float(data['mEstimatedMininumPowerConsumption']),
            'power_produced': 0}

def load_generators(classes, machines, recipes, all_items):
    for data in classes:
        power_production = float(data['mPowerProduction'])

        machines[data['ClassName']] = {
            'name': data['mDisplayName'],
            'power_use': 0,
            'power_produced': power_production}
        
        for fuel_data in data['mFuel']:
            if fuel_data['mFuelClass'] in all_items:
                time = all_items[fuel_data['mFuelClass']]['energy']/power_production
                recipes[data['ClassName'] + '_' + fuel_data['mFuelClass']] = {
                    'name': data['mDisplayName'] + ' (' + all_items[fuel_data['mFuelClass']]['name'] + ')',
                    'time': time,
                    'ingredients': extract_generator_ingredients(data, fuel_data, power_production, time),
                    'products': extract_generator_byproduct(fuel_data, power_production, time),
                    'machine': data['ClassName'],
                    'power_use': 0.0}
                
def extract_generator_ingredients(data, fuel_data, power_production, time):
    ingredients = [{'item': fuel_data['mFuelClass'], 'amount': 1}]
    if fuel_data['mSupplementalResourceClass'] is not '':
        ingredients.append({'item': fuel_data['mSupplementalResourceClass'], 'amount': (((60/(1000/power_production))*float(data['mSupplementalToPowerRatio']))/60)*time})
    return ingredients

def extract_generator_byproduct(fuel_data, power_production, time):
    byproduct = [{'item': 'Power_Produced', 'amount': power_production*time/60}]
    if fuel_data['mByproduct'] is not '':
        byproduct.append({'item': fuel_data['mByproduct'], 'amount': float(fuel_data['mByproductAmount'])})
    return byproduct

read_docs('Docs.json')