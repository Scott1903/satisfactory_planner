import os
import sys
# redirect stdout and stderr because Windows is dumb
if sys.stdout is None or sys.stderr is None:
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w') 

import PySimpleGUI as sg
import json
from main import optimize_production

# Check if GLPK_PATH environment variable is set
glpk_path = os.getenv('GLPK_PATH')
if glpk_path is None:
    # Show a popup if the environment variable is not set
    sg.Popup(
        "Environment Variable Not Set",
        "The GLPK_PATH environment variable is not set. Install GLPK solver and set the path where GLPK is installed.",
        "On Windows:",
        "1. Open System Control Panel (Win+X, then select System).",
        "2. Go to Advanced System Settings.",
        "3. Click on Environment Variables.",
        "4. Click New under System variables.",
        "5. Enter the path to the glpsol.exe:",
        "   Variable Name: GLPK_PATH",
        "   Variable Value: (example, E:\\Applications\\pyomo glpk\\glpk-4.65\\w64).",
        "Restart your PC after setting the variable."
    )

# Load data from data.json
data_file = 'Data\data.json'
try:
    with open(data_file, 'r') as file:
        data = json.load(file)
except Exception as e:
    sg.popup_error(f"Failed to load file: {e}")
    data = None

# Load settings on saved.json
def load_settings(filename):
    try:
        with open(filename, 'r') as file:
            settings = json.load(file)
        return settings
    except FileNotFoundError:
        return None

# Function to save settings
def save_settings(filename):
    with open(filename, 'w') as file:
        json.dump(settings, file)

# Create 'Saves' directory if it doesn't exist
if not os.path.exists('Saves'):
    os.makedirs('Saves')

# Extract recipes and their names from the data
recipes = {key: data['recipes'][key]['name'] for key in data['recipes']}

# Load default settings on startup
settings = load_settings('Saves/default.json')

# Separate recipes into regular and alternate lists
regular_recipes = sorted([(key, name) for key, name in recipes.items() if not name.startswith('Alternate')], key=lambda x: x[1])
alternate_recipes = sorted([(key, name) for key, name in recipes.items() if name.startswith('Alternate')], key=lambda x: x[1])

# Extract items and their names from the data
products = {p['item'] for recipe in data['recipes'].values() for p in recipe['products']}
items = {key: data['items'][key]['name'] for key in data['items'] if key in products}

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
        for key, value in settings['resource_limits'].items()
    ]
]

# Info texts for weights
weight_info = {
    'Power Use': 'Penalty for power used. \
                \n\nThe to total MW of power used to produce output. \
                \n\nFor nuclear power plants, \n1 MW requires 0.143 resources*. \
                \nFor fuel power plants, \n1 MW requires 0.055 resources*. \
                \nWhen running max sink points, \n1 MW requires 0.084 resources*. \
                \n\nRecommended [0.094] for resource optimization. \nRecommended [0.3] for minimizing infrastructure need.',
    'Item Use': 'Penalty for items to belt. \
                \n\nThe sum of all items produced/recycled. \
                \n\nValues >= 0.4 will start removing screw recipes. \
                \n\nRecommended [0] for resource optimization. \nRecommended [0.4] for simplifying production.',
    'Building Use': 'Penalty for machine count. \
                \n\nThe total miners, smelters, assemblers, ect. \
                \n\nRecommended [0] instead use buildings_scaled.',
    'Resource Use': 'Penalty for raw resource use. \
                \n\nThe total raw resources (all scaled equally). \
                \n\nRecommended [0] instead use resources_scaled.',
    'Buildings Scaled': 'Penalty for complex machines. \
                \n\nThe sum of (#inputs + #outputs - 1)^1.584963/3 * n machines. \
                \n1 full Manufacturer = 3 Assemblers = 9 Constructors. \
                \n\nValues >= 10 will start prioritizing more Smelters over Refineries (Iron, Caterium). \
                \n\nRecommended [0] for resource optimization. \nRecommended [20] for simplifying production.',
    'Resources Scaled': 'Penalty for rare resource use. \
                \n\nThe total resources used scaled by limits provided. \
                \n\nTo give Water no penalty, set Water to very high limit. \
                \n\nRecommended [1].',
    'Nuclear Waste': 'Penalty for not sinking Nuclear Waste products. \
                \n\nRecommended [9999999] very high value.',
}

# Layout for weights page
weights_layout = [
    [sg.Text('Weights', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    *[
        [sg.Text(key, size=(20, 1)), sg.InputText(default_text=str(value), key=f"weight_{key}", size=(10, 1)), sg.Button('Info', key=f"info_{key}")]
        for key, value in settings['weights'].items()
    ]
]

# Layout for recipes page with two columns
recipes_layout = [
    [sg.Text('Recipes', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    [
        sg.Column([
            [sg.Text('Regular Recipes'), sg.Checkbox('Select All', default=True, key='regular_select_all', enable_events=True)],
            *[[sg.Checkbox(name, default=True, key=f"recipe_{key}")] for key, name in regular_recipes]
        ], scrollable=True, vertical_scroll_only=True, size=(250, 300)),
        sg.Column([
            [sg.Text('Alternate Recipes'), sg.Checkbox('Select All', default=True, key='alternate_select_all', enable_events=True)],
            *[[sg.Checkbox(name, default=True, key=f"recipe_{key}")] for key, name in alternate_recipes]
        ], scrollable=True, vertical_scroll_only=True, size=(250, 300))
    ]
]

# Function to create input layout
def create_input_layout(key_suffix, visible=True):
    return [
        sg.Combo([name for _, name in sorted_items], default_value='', key=f'input_item_{key_suffix}', enable_events=True, size=(30, 1), visible=visible),
        sg.InputText(default_text='0', key=f'input_amount_{key_suffix}', size=(10, 1), visible=visible)
    ]

# Initial layout for inputs
input_layout = [
    [sg.Text('Inputs', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    create_input_layout(0),
    [sg.Button('Add Input'), sg.Button('Remove Input')]
]

# Function to create output layout
def create_output_layout(key_suffix, visible=True):
    return [
        sg.Combo([name for _, name in sorted_items], default_value='', key=f'output_item_{key_suffix}', enable_events=True, size=(30, 1), visible=visible),
        sg.InputText(default_text='0', key=f'output_amount_{key_suffix}', size=(10, 1), visible=visible),
        sg.Checkbox('Maximize this item', key=f'output_checkbox_{key_suffix}', enable_events=True, visible=(key_suffix == 0 and visible))  # Only visible for the first item
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

# Layout for products
products_layout = [
    [sg.Text('Products', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    [sg.Multiline(size=(80, 20), key='products_output')]
]

# Layout for ingredients
ingredients_layout = [
    [sg.Text('Ingredients', font=('Helvetica', 16), text_color=sg.LOOK_AND_FEEL_TABLE['Modern']['ACCENT1'])],
    [sg.Multiline(size=(80, 20), key='ingredients_output')]
]

# Main layout with Tabs
layout = [
    [sg.TabGroup([
        [sg.Tab('Resource Limits', resource_layout), 
         sg.Tab('Weights', weights_layout),
         sg.Tab('Recipes', recipes_layout),
         sg.Tab('Inputs', input_layout),
         sg.Tab('Outputs', output_layout),
         sg.Tab('Results', results_layout),
         sg.Tab('Products', products_layout),
         sg.Tab('Ingredients', ingredients_layout)]
    ])]
]

window = sg.Window('Satisfactory Optimization Tool - 1.0', layout, finalize=True)

# Update recipe checkboxes based on settings
for key in recipes:
    window[f'recipe_{key}'].update(value=key not in settings['recipes_off'])

input_key_suffix = 1
highest_input_key = 1
output_key_suffix = 1
highest_output_key = 1

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
    elif event.startswith('info_'):
        key = event.split('_')[1]
        sg.popup(key, weight_info.get(key, 'No information available.'))

    # Handle select all recipe checkboxes
    elif event == 'regular_select_all':
        for key, _ in regular_recipes:
            window[f'recipe_{key}'].update(values['regular_select_all'])
    elif event == 'alternate_select_all':
        for key, _ in alternate_recipes:
            window[f'recipe_{key}'].update(values['alternate_select_all'])

    # Handle add input button
    elif event == 'Add Input':
        if input_key_suffix < highest_input_key:
            window[f'input_item_{input_key_suffix}'].update(visible=True)
            window[f'input_amount_{input_key_suffix}'].update(visible=True)
        else:
            window.extend_layout(window['Inputs'], [create_input_layout(input_key_suffix)])
        input_key_suffix += 1
        highest_input_key = max(highest_input_key, input_key_suffix)

    # Handle remove input button
    elif event == 'Remove Input' and input_key_suffix > 1:
        input_key_suffix -= 1
        window[f'input_item_{input_key_suffix}'].update(visible=False)
        window[f'input_amount_{input_key_suffix}'].update(visible=False)

    # Handle add output button
    elif event == 'Add Output':
        if output_key_suffix < highest_output_key:
            window[f'output_item_{output_key_suffix}'].update(visible=True)
            window[f'output_amount_{output_key_suffix}'].update(visible=True)
        else:
            window.extend_layout(window['Outputs'], [create_output_layout(output_key_suffix)])
        output_key_suffix += 1
        highest_output_key = max(highest_output_key, output_key_suffix)

    # Handle remove output button
    elif event == 'Remove Output' and output_key_suffix > 1:
        output_key_suffix -= 1
        window[f'output_item_{output_key_suffix}'].update(visible=False)
        window[f'output_amount_{output_key_suffix}'].update(visible=False)

    # Handle maximize checkbox
    elif event.startswith('output_checkbox_'):
        key_suffix = int(event.split('output_checkbox_')[1])
        if values[event] and key_suffix == 0:
            settings['max_item'] = sorted_items[0][0]  # Use first item as an example
        else:
            settings['max_item'] = False

    # Handle save settings button
    elif event == 'Save Settings':
        try:
            settings['resource_limits'] = {key: float(values[f'resource_{key}']) for key in settings['resource_limits']}
            settings['weights'] = {key: float(values[f'weight_{key}']) for key in settings['weights']}
            settings['recipes_off'] = [key for key in recipes if not values[f'recipe_{key}']]
            settings['inputs'] = {key: float(values[f'input_amount_{i}']) for i in range(input_key_suffix) for key, name in sorted_items if name == values[f'input_item_{i}']}
            settings['outputs'] = {key: float(values[f'output_amount_{i}']) for i in range(output_key_suffix) for key, name in sorted_items if name == values[f'output_item_{i}']}
            settings['max_item'] = next((key for key, name in sorted_items if name == values['output_item_0']), False) if values.get('output_checkbox_0') else False

            save_filename = sg.popup_get_file('Save settings as', save_as=True, no_window=True, default_extension=".json", file_types=(("JSON Files", "*.json"),), initial_folder='Saves')
        except Exception as e:
            sg.popup_error(f"Error saving variables: {e}")
        if save_filename:
            save_settings(save_filename)
            sg.popup(f"Settings saved to {save_filename}")

    # Handle load settings button
    elif event == 'Load Settings':
        load_filename = sg.popup_get_file('Load settings from', no_window=True, file_types=(("JSON Files", "*.json"),), initial_folder='Saves')
        if load_filename:
            loaded_settings = load_settings(load_filename)
            if loaded_settings:
                settings.update(loaded_settings)
                # Load resource limits
                for key, value in settings['resource_limits'].items():
                    window[f'resource_{key}'].update(value)
                # Load weights
                for key, value in settings['weights'].items():
                    window[f'weight_{key}'].update(value)
                # Load recipe checkboxes
                for key in recipes:
                    window[f'recipe_{key}'].update(key not in settings['recipes_off'])
                # Reset existing input rows
                for i in range(1, highest_input_key):
                    window[f'input_item_{i}'].update(visible=False)
                    window[f'input_amount_{i}'].update(visible=False)
                input_key_suffix = 1
                # Load input rows
                for i, (item, amount) in enumerate(settings['inputs'].items()):
                    if i > 0:
                        if input_key_suffix < highest_input_key:
                            window[f'input_item_{input_key_suffix}'].update(visible=True)
                            window[f'input_amount_{input_key_suffix}'].update(visible=True)
                        else:
                            window.extend_layout(window['Inputs'], [create_input_layout(input_key_suffix)])
                        input_key_suffix += 1
                        highest_input_key = max(highest_input_key, input_key_suffix)
                    window[f'input_item_{i}'].update(items[item])
                    window[f'input_amount_{i}'].update(amount)
                # Reset existing output rows
                for i in range(1, highest_output_key):
                    window[f'output_item_{i}'].update(visible=False)
                    window[f'output_amount_{i}'].update(visible=False)
                    window[f'output_checkbox_{i}'].update(visible=False)
                output_key_suffix = 1
                # Load output rows
                for i, (item, amount) in enumerate(settings['outputs'].items()):
                    if i > 0:
                        if output_key_suffix < highest_output_key:
                            window[f'output_item_{output_key_suffix}'].update(visible=True)
                            window[f'output_amount_{output_key_suffix}'].update(visible=True)
                        else:
                            window.extend_layout(window['Outputs'], [create_output_layout(output_key_suffix)])
                        output_key_suffix += 1
                        highest_output_key = max(highest_output_key, output_key_suffix)
                    window[f'output_item_{i}'].update(items[item])
                    window[f'output_amount_{i}'].update(amount)
                # Load maximize checkbox
                if settings['max_item']:
                    window[f'output_checkbox_{0}'].update(True)
                else:
                    window[f'output_checkbox_{0}'].update(False)

                sg.popup(f"Settings loaded from {load_filename}")
            else:
                sg.popup_error(f"Failed to load settings from {load_filename}")

    # Handle reset button
    elif event == 'Reset':
        settings = load_settings('Saves/default.json')

        for key, value in settings['resource_limits'].items():
            window[f'resource_{key}'].update(value)
        for key, value in settings['weights'].items():
            window[f'weight_{key}'].update(value)
        for key in recipes:
            window[f'recipe_{key}'].update(key not in settings['recipes_off'])
        # Inputs
        window[f'input_item_{0}'].update('')
        window[f'input_amount_{0}'].update('0')
        for i in range(1, highest_output_key):
            window[f'input_item_{i}'].update('')
            window[f'input_amount_{i}'].update(0)
            window[f'input_item_{i}'].update(visible=False)
            window[f'input_amount_{i}'].update(visible=False)
        input_key_suffix = 1
        # Outputs
        window[f'output_item_{0}'].update('')
        window[f'output_amount_{0}'].update('0')
        window[f'output_checkbox_{0}'].update(False)
        for i in range(1, highest_output_key):
            window[f'output_item_{i}'].update('')
            window[f'output_amount_{i}'].update(0)
            window[f'output_item_{i}'].update(visible=False)
            window[f'output_amount_{i}'].update(visible=False)
            window[f'output_checkbox_{i}'].update(visible=False)
        output_key_suffix = 1
        # Windows
        window['results_output'].update('')
        window['products_output'].update('')
        window['ingredients_output'].update('')
        sg.popup("Settings reset to default values.")

    # Handle run optimization button
    elif event == 'Run Optimization':
        try:
            settings['resource_limits'] = {key: float(values[f'resource_{key}']) for key in settings['resource_limits']}
            settings['weights'] = {key: float(values[f'weight_{key}']) for key in settings['weights']}
            settings['recipes_off'] = [key for key in recipes if not values[f'recipe_{key}']]
            settings['inputs'] = {key: float(values[f'input_amount_{i}']) for i in range(input_key_suffix) for key, name in sorted_items if name == values[f'input_item_{i}']}
            settings['outputs'] = {key: float(values[f'output_amount_{i}']) for i in range(output_key_suffix) for key, name in sorted_items if name == values[f'output_item_{i}']}
            settings['max_item'] = next((key for key, name in sorted_items if name == values['output_item_0']), False) if values.get('output_checkbox_0') else False
            if values['output_item_0'] == 'Points':
                settings['max_item'] = 'Points'
                for key, limit in settings['resource_limits'].items():
                    if limit == 0:
                        settings['resource_limits'][key] = 0.00001  # Prevent divide-by-zero error
            results = optimize_production(data, settings)

            # Results tab
            results_output = ''
            if settings['max_item'] == 'Points':
                results_output += 'Sink Points: {}\n\n'.format(round(results.get('sink_points', 0), 1))
            if results.get('items_input', {}):
                results_output = 'Items Given:\n'
                results_output += '\n'.join(f"{item}: {round(amount, 2)}" for item, amount in sorted(results.get('items_input', {}).items()))
                results_output += '\n\n'
            results_output += 'Items Returned:\n'
            results_output += '\n'.join(f"{item}: {round(amount, 2)}" for item, amount in sorted(results.get('items_output', {}).items()))
            if results.get('power_produced', 0) > 0.01:
                results_output += '\n\nResource*/Power Ratio: ' + str(round(results.get('resources_scaled', 0)/(results.get('power_produced', 0) - results.get('power_use', 0)), 2))
            results_output += '\n\nResources:\n'
            r_limits = {data['resources'][r]['name']: lim for r, lim in settings['resource_limits'].items()}
            results_output += '\n'.join(f"{resource}: {round(amount, 2)} ({round(amount/r_limits[resource]*100,1)}%)" for resource, amount in sorted(results.get('resources_needed', {}).items()))
            results_output += '\n\nRecipes:\n'
            results_output += '\n'.join(f"{recipe} [{round(amount, 2)}]" for recipe, amount in sorted(results.get('recipes_used', {}).items()))
            results_output += '\n\n'
            results_output += 'Items In Production Chain:\n'
            results_output += '\n'.join(f"{item}: {round(amount, 2)}" for item, amount in sorted(results.get('items_needed', {}).items()))
            results_output += '\n\n'
            # --------- For Tests --------
            #results_output += 'Items Not Needed:\n'
            #results_output += '\n'.join(f"{item}: {round(amount, 2)}" for item, amount in sorted(results.get('items_not_needed', {}).items()))
            #results_output += '\n\n'
            # --------- For Tests --------
            results_output += 'Power Used: {}\n'.format(round(results.get('power_use', 0), 1))
            results_output += 'Items: {}\n'.format(round(results.get('item_use', 0), 1))
            results_output += 'Buildings: {}\n'.format(round(results.get('buildings', 0), 1))
            results_output += 'Resources: {}\n'.format(round(results.get('resources', 0), 1))
            results_output += 'Buildings*: {}\n'.format(round(results.get('buildings_scaled', 0), 1))
            results_output += 'Resources*: {}\n'.format(round(results.get('resources_scaled', 0), 1))
            window['results_output'].update(results_output)

            # Products tab
            all_items = {**results['items_needed'], **results['resources_needed']}
            results_output = ['Products Map:']
            for ingredient, map in sorted(results['products_map'].items()):
                results_output.append(f"\n\n{ingredient} ({round(all_items[ingredient], 2)})")
                for recipe, num in sorted(map.items()):
                    results_output.append(f"\n{round(num, 2)} -> {recipe} [{round(results['recipes_used'][recipe], 2)}]")
            window['products_output'].update(''.join(results_output))

            # Ingredients tab
            results_output = ['Ingredients Map:']
            for recipe, map in sorted(results['ingredients_map'].items()):
                results_output.append(f"\n\n{recipe} [{round(results['recipes_used'][recipe], 2)}]")
                for ingredient, num in sorted(map.items()):
                    results_output.append(f"\n<- {round(num, 2)}  {ingredient}")
            window['ingredients_output'].update(''.join(results_output))

        except Exception as e:
            sg.popup_error(f"Error running optimization: {e}")

window.close()
