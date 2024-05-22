import PySimpleGUI as sg
import json
import os
from main import optimize_production

# Load data from data.json
data_file = 'data.json'
try:
    with open(data_file, 'r') as file:
        data = json.load(file)
except Exception as e:
    sg.popup_error(f"Failed to load file: {e}")
    data = None

# Default Settings
def default_settings():
    return {
        'resource_limits': {
            'Desc_Water_C': 100000,
            'Desc_OreGold_C': 11040,
            'Desc_RawQuartz_C': 10500,
            'Desc_Coal_C': 30120,
            'Desc_NitrogenGas_C': 12000,
            'Desc_OreIron_C': 70380,
            'Desc_Sulfur_C': 6840,
            'Desc_OreBauxite_C': 9780,
            'Desc_OreUranium_C': 2100,
            'Desc_Stone_C': 52860,
            'Desc_LiquidOil_C': 11700,
            'Desc_OreCopper_C': 28860},
        'weights': {
            'Power Use': 0.1,
            'Item Use': 0.3,
            'Building Use': 0,
            'Resource Use': 0,
            'Buildings Scaled': 1,
            'Resources Scaled': 1,
            'Uranium Waste': 999999},
        'recipes_off': [],
        'outputs': {},
        'max_item': False}

settings = default_settings()
resource_limits = settings['resource_limits']
weights = settings['weights']
recipes_off = settings['recipes_off']
outputs = settings['outputs']
max_item = settings['max_item']

# Load settings on saved.json
def load_settings(filename='saved.json'):
    try:
        with open(filename, 'r') as file:
            settings = json.load(file)
        return settings
    except FileNotFoundError:
        return None

# Function to save settings
def save_settings(filename='saved.json'):
    settings = {
        'resource_limits': resource_limits,
        'weights': weights,
        'recipes_off': recipes_off,
        'outputs': outputs,
        'max_item': max_item
    }
    with open(filename, 'w') as file:
        json.dump(settings, file)

# Create 'Saves' directory if it doesn't exist
if not os.path.exists('Saves'):
    os.makedirs('Saves')

# Extract recipes and their names from the data
recipes = {}
if data and 'recipes' in data:
    recipes = {key: data['recipes'][key]['name'] for key in data['recipes']}

# Separate recipes into regular and alternate lists
regular_recipes = sorted([(key, name) for key, name in recipes.items() if not name.startswith('Alternate')], key=lambda x: x[1])
alternate_recipes = sorted([(key, name) for key, name in recipes.items() if name.startswith('Alternate')], key=lambda x: x[1])

# Extract items and their names from the data
items = {}
if data and 'items' in data:
    items = {key: data['items'][key]['name'] for key in data['items']}

# Sort items alphabetically
sorted_items = sorted(items.items(), key=lambda x: x[1])

# Apply a modern theme
sg.LOOK_AND_FEEL_TABLE['Modern'] = {'BACKGROUND': '#f2f2f2',
                                          'TEXT': '#000000',
                                          'INPUT': '#ffffff',
                                          'TEXT_INPUT': '#000000',
                                          'SCROLL': '#ffffff',
                                          'BUTTON': ('#000000', '#d3dfed'),
                                          'PROGRESS': sg.DEFAULT_PROGRESS_BAR_COLOR,
                                          'BORDER': 1,
                                          'SLIDER_DEPTH': 0,
                                          'PROGRESS_DEPTH': 0,
                                          'ACCENT1': '#405369'}

sg.theme('Modern')

# Layout for resource limits page
resource_layout = [
    [sg.Text('Resource Limits', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    *[
        [sg.Text(data['resources'][key]['name'], size=(20, 1)), sg.InputText(default_text=str(value), key=f"resource_{key}", size=(10, 1))]
        for key, value in resource_limits.items()
    ]
]

# Info texts for weights
weight_info = {
    'Power Use': 'Penalty for power used. \
                \n\nThe to total MW of power used to produce output. \
                \n\nFor most power sources late-game,\n1 MW requires 0.1 resources* \
                \n\nRecommended [0.1] between 0.08 and 0.28.',
    'Item Use': 'Penalty for items to belt. \
                \n\nThe sum of all items produced/recycled. \
                \n\nValues >= 0.3 will start removing screw recipes. \
                \n\nRecommended [0.3] between 0 and 1.',
    'Building Use': 'Penalty for machine count. \
                \n\nThe total miners, smelters, assemblers, ect. \
                \n\nRecommended [0] to use buildings_scaled.',
    'Resource Use': 'Penalty for raw resource use. \
                \n\nThe total raw resources (all scaled equally). \
                \n\nRecommended [0] to use resources_scaled.',
    'Buildings Scaled': 'Penalty for complex machines. \
                \n\nThe sum of (#inputs + #outputs - 1)^2 * n machines. \
                \n\nValues >= 1 will start prioritizing more Smelters over Refineries (Copper, Iron, Caterium). \
                \n\nRecommended [1] between 0 and 4.',
    'Resources Scaled': 'Penalty for rare resource use. \
                \n\nThe total resources used scaled by limits provided. \
                \n\nTo give Water no penalty, set Water to very high limit. \
                \n\nRecommended [1].',
    'Uranium Waste': 'Penalty for not sinking Uranium Waste products. \
                \n\nRecommended [999999] very high value.',
}

# Layout for weights page
weights_layout = [
    [sg.Text('Weights', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    *[
        [sg.Text(key, size=(20, 1)), sg.InputText(default_text=str(value), key=f"weight_{key}", size=(10, 1)), sg.Button('Info', key=f"info_{key}")]
        for key, value in weights.items()
    ]
]

# Layout for recipes page with two columns
recipes_layout = [
    [sg.Text('Recipes', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    [
        sg.Column([[sg.Text('Regular Recipes')]] + [[sg.Checkbox(name, default=True, key=f"recipe_{key}")] for key, name in regular_recipes], scrollable=True, vertical_scroll_only=True, size=(250, 300)),
        sg.Column([[sg.Text('Alternate Recipes')]] + [[sg.Checkbox(name, default=True, key=f"recipe_{key}")] for key, name in alternate_recipes], scrollable=True, vertical_scroll_only=True, size=(250, 300))
    ]
]

# Function to create output layout
def create_output_layout(key_suffix):
    return [
        sg.Combo([name for _, name in sorted_items], default_value='', key=f'output_item_{key_suffix}', enable_events=True, size=(30, 1)),
        sg.InputText(default_text='0', key=f'output_amount_{key_suffix}', size=(10, 1)),
        sg.Checkbox('Maximize this item', key=f'output_checkbox_{key_suffix}', enable_events=True, visible=(key_suffix == 0))  # Only visible for the first item
    ]

# Initial layout for outputs
output_layout = [
    [sg.Text('Outputs', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    create_output_layout(0),
    [sg.Button('Add Output'), sg.Button('Remove Output')]
]

# Layout for results
results_layout = [
    [sg.Text('Results', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1']), sg.Button('Run Optimization'), sg.Button('Save Settings'), sg.Button('Load Settings'), sg.Button('Reset')],
    [sg.Multiline(size=(80, 20), key='results_output')]
]

# Main layout with Tabs
layout = [
    [sg.TabGroup([
        [sg.Tab('Resource Limits', resource_layout), 
         sg.Tab('Weights', weights_layout),
         sg.Tab('Recipes', recipes_layout),
         sg.Tab('Outputs', output_layout),
         sg.Tab('Results', results_layout)]
    ])]
]

window = sg.Window('Satisfactory Optimization Tool - Update 8', layout)

output_key_suffix = 1
highest_key_suffix = 1

def parse_input(input_str):
    try:
        return json.loads(input_str.replace("'", '"'))
    except json.JSONDecodeError as e:
        sg.popup_error(f"Error parsing input: {e}")
        return None

while True:
    event, values = window.read()

    if event == sg.WINDOW_CLOSED:
        break

    # Handle info buttons
    if event.startswith('info_'):
        key = event.split('_')[1]
        sg.popup(key, weight_info.get(key, 'No information available.'))

    # Handle add output button
    elif event == 'Add Output':
        window.extend_layout(window['Outputs'], [create_output_layout(output_key_suffix)])
        output_key_suffix += 1
        highest_key_suffix = max(highest_key_suffix, output_key_suffix)

    # Handle remove output button
    if event == 'Remove Output' and output_key_suffix > 1:
        output_key_suffix -= 1
        for suffix in range(output_key_suffix, highest_key_suffix):
            window[f'output_item_{suffix}'].update(visible=False)
            window[f'output_amount_{suffix}'].update(visible=False)
            window[f'output_amount_{suffix}'].hide_row()

    # Handle maximize checkbox
    if event.startswith('output_checkbox_'):
        key_suffix = int(event.split('output_checkbox_')[1])
        if values[event] and key_suffix == 0:
            max_item = sorted_items[0][0]  # Use first item as an example
        else:
            max_item = False

    # Handle save settings button
    if event == 'Save Settings':
        try:
            resource_limits = {key: float(values[f'resource_{key}']) for key in resource_limits}
            weights = {key: float(values[f'weight_{key}']) for key in weights}
            recipes_off = [key for key in recipes if not values[f'recipe_{key}']]
            outputs = {key: float(values[f'output_amount_{i}']) for i in range(output_key_suffix) for key, name in sorted_items if name == values[f'output_item_{i}']}
            max_item = next((key for key, name in sorted_items if name == values['output_item_0']), False) if values.get('output_checkbox_0') else False

            save_filename = sg.popup_get_file('Save settings as', save_as=True, no_window=True, default_extension=".json", file_types=(("JSON Files", "*.json"),), initial_folder='Saves')
        except Exception as e:
            sg.popup_error(f"Error saving variables: {e}")
        if save_filename:
            save_settings(save_filename)
            sg.popup(f"Settings saved to {save_filename}")

    # Handle load settings button
    if event == 'Load Settings':
        load_filename = sg.popup_get_file('Load settings from', no_window=True, file_types=(("JSON Files", "*.json"),), initial_folder='Saves')
        if load_filename:
            loaded_settings = load_settings(load_filename)
            if loaded_settings:
                settings.update(loaded_settings)
                resource_limits = settings['resource_limits']
                weights = settings['weights']
                recipes_off = settings['recipes_off']
                outputs = settings['outputs']
                max_item = settings['max_item']

                for key, value in resource_limits.items():
                    window[f'resource_{key}'].update(value)
                for key, value in weights.items():
                    window[f'weight_{key}'].update(value)
                for key in recipes:
                    window[f'recipe_{key}'].update(key not in recipes_off)
                for i, (item, amount) in enumerate(outputs.items()):
                    if i >= output_key_suffix:
                        window.extend_layout(window['Outputs'], [create_output_layout(output_key_suffix)])
                        output_key_suffix += 1
                        highest_key_suffix = max(highest_key_suffix, output_key_suffix)
                    window[f'output_item_{i}'].update(items[item])
                    window[f'output_amount_{i}'].update(amount)
                sg.popup(f"Settings loaded from {load_filename}")
            else:
                sg.popup_error(f"Failed to load settings from {load_filename}")

    # Handle reset button
    if event == 'Reset':
        settings = default_settings()
        resource_limits = settings['resource_limits']
        weights = settings['weights']
        recipes_off = settings['recipes_off']
        outputs = settings['outputs']
        max_item = settings['max_item']

        for key, value in resource_limits.items():
            window[f'resource_{key}'].update(value)
        for key, value in weights.items():
            window[f'weight_{key}'].update(value)
        for key in recipes:
            window[f'recipe_{key}'].update(True)
        for i in range(output_key_suffix):
            window[f'output_item_{i}'].update('')
            window[f'output_amount_{i}'].update('0')
        window[f'output_checkbox_{0}'].update(False)
        output_key_suffix = 1
        highest_key_suffix = 1
        window['results_output'].update('')
        sg.popup("Settings reset to default values.")

    # Handle run optimization button
    if event == 'Run Optimization':
        try:
            resource_limits = {key: float(values[f'resource_{key}']) for key in resource_limits}
            weights = {key: float(values[f'weight_{key}']) for key in weights}
            recipes_off = [key for key in recipes if not values[f'recipe_{key}']]
            outputs = {key: float(values[f'output_amount_{i}']) for i in range(output_key_suffix) for key, name in sorted_items if name == values[f'output_item_{i}']}
            max_item = next((key for key, name in sorted_items if name == values['output_item_0']), False) if values.get('output_checkbox_0') else False

            results = optimize_production(data, resource_limits, outputs, recipes_off, weights, max_item)
            results_output = 'Items Outputed:\n'
            results_output += '\n'.join(f"{item}: {round(amount, 2)}" for item, amount in sorted(results.get('items_output', {}).items()))
            results_output += '\n\nResources Needed:\n'
            results_output += '\n'.join(f"{resource}: {round(amount, 2)}" for resource, amount in sorted(results.get('resources_needed', {}).items()))
            results_output += '\n\nItems Needed:\n'
            results_output += '\n'.join(f"{item}: {round(amount, 2)}" for item, amount in sorted(results.get('items_needed', {}).items()))
            results_output += '\n\nRecipes Used:\n'
            results_output += '\n'.join(f"{recipe}: {round(amount, 2)}" for recipe, amount in sorted(results.get('recipes_used', {}).items()))
            results_output += '\n\nPower Produced: {}\n'.format(round(results.get('power_produced', 0), 1))
            results_output += '\nPower Used: {}\n'.format(round(results.get('power_use', 0), 1))
            results_output += 'Items: {}\n'.format(round(results.get('item_use', 0), 1))
            results_output += 'Buildings: {}\n'.format(round(results.get('buildings', 0), 1))
            results_output += 'Resources: {}\n'.format(round(results.get('resources', 0), 1))
            results_output += 'Buildings*: {}\n'.format(round(results.get('buildings_scaled', 0), 1))
            results_output += 'Resources*: {}\n'.format(round(results.get('resources_scaled', 0), 1))
            window['results_output'].update(results_output)
        except Exception as e:
            sg.popup_error(f"Error running optimization: {e}")

window.close()
