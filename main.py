import tkinter as tk
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


# Define the Node class
class Node:
    def __init__(self, role, content, parent=None, tool_call_id=None, name=None):
        self.parent = parent
        self.role = role
        self.tool_call_id = tool_call_id
        self.name = name
        self.content = content
        self.children = []


# Function to traverse up the tree and convert the messages to json
def messages_to_json(current_node):
    stack = []  # Stack of dictionaries of messages
    # Goes through all the nodes up to the root and puts their info in correct order into stack
    while current_node.parent is not None:
        # Add tool-specific fields if the role is "tool"
        if current_node.role != "tool":
            message = {
                "role": current_node.role,
                "content": current_node.content
            }
        else:
            message = {
                "role": current_node.role,
                "tool_call_id": current_node.tool_call_id,
                "name": current_node.name,
                "content": current_node.content
            }

        stack.append(message)
        current_node = current_node.parent

    stack.reverse()

    result = {"messages": stack}

    return json.dumps(result)


# This function is called when the jump into convo button is clicked
def jump_into_convo():
    global selected_node

    if selected_node is not None:
        print(messages_to_json(selected_node))


# Function to handle adding a child node
def branch_from_node():
    global selected_node, ax, tree, canvas

    if selected_node is not None:

        if selected_node.children != []: # Cannot branch from a leaf node

            new_node_name = selected_node.children[0].role # Puts the same name as the child
            if new_node_name:
                new_node = Node(new_node_name, new_node_name, selected_node)
                selected_node.children.append(new_node)

                # Clear and redraw plot
                ax.clear()
                ax.set_xlim(-10, 10)
                ax.set_ylim(-2, depth * step_y + 2)
                ax.axis('off')

                plot_tree(ax, tree, 0, depth * step_y, step_x, step_y)
                canvas.draw()
        else:
            print('Not allowed to branch from a leaf node')

# Function to handle node click event
def on_node_click(event):
    global selected_node, current_annotation, text_widget

    if event.inaxes is not None:
        # Clear existing annotation if present
        if current_annotation:
            current_annotation.remove()
            current_annotation = None

        for node, (x, y) in node_positions.items():
            if abs(event.xdata - x) < 0.75 and abs(event.ydata - y) < 0.75:
                selected_node = node
                context_menu(event)
                # Update text widget with information about the clicked node
                text_widget.config(state=tk.NORMAL)
                text_widget.delete('1.0', tk.END)
                text_widget.insert(tk.END, f"Selected Node: {node.role}\n\n"
                                           f"{node.content}")
                text_widget.config(state=tk.DISABLED)
                break

# Function to show context menu for creating a child node
def context_menu(event):
    global selected_node, current_annotation

    if selected_node is not None:
        current_annotation = ax.annotate(
            "Enter child node name:",
            xy=(event.xdata, event.ydata),
            xycoords='data',
            xytext=(-40, 20),
            textcoords='offset points',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2"),
        )
        canvas.draw()

# Function to recursively add nodes to the plot
def plot_tree(ax, node, x, y, step_x, step_y):
    global node_positions
    ax.text(x, y, node.role, bbox=dict(facecolor='lightblue', alpha=0.5),
            ha='center', va='center', fontsize=12)
    node_positions[node] = (x, y)

    # Calculate positions for children
    if len(node.children) > 0:
        child_spacing = step_x * (len(node.children) - 1) / 2
        for i, child in enumerate(node.children):
            plot_tree(ax, child, x - child_spacing + i * step_x, y - step_y, step_x, step_y)
            ax.plot([x, x - child_spacing + i * step_x], [y, y - step_y], 'k-')

# Sample tree structure
def create_sample_tree():
    root = Node("Conversation", "Conversation")

    youngest = root

    for message in result['messages']:
        if 'tool_call_id' in message:
            newNode = Node(message['role'], message['content'], youngest, message['tool_call_id'], message['name'])
        else:
            newNode = Node(message['role'], message['content'], youngest)
        youngest.children = [newNode]
        youngest = newNode

    return root

# Load and parse the JSON
messages = {"messages": [{"role": "system",
                          "content": "You are a helpful assistant with access to the following functions. Use them if required -\n{\n    \"type\": \"function\",\n    \"function\": {\n        \"name\": \"execute_python\",\n        \"description\": \"Run a command in a python interpreter\",\n        \"parameters\": {\n            \"type\": \"object\",\n            \"properties\": {\n                \"code\": {\n                    \"type\": \"string\",\n                    \"description\": \"Python code to execute\",\n                }\n            },\n            \"required\": [\"code\"],\n        }\n    }\n}\n                \nTo use these functions respond with:\n<functioncall>\n{\n    \"name\": \"function_name\",\n    \"arguments\": {\n        \"arg_1\": \"value_1\",\n        \"arg_1\": \"value_1\",\n         ...\n    }\n}\n</functioncall>\n\nEdge cases you must handle:\n - If there are no functions that match the user request, you will respond politely that you cannot help.\n\nThe data is found in ./data/WiGLE.json"},
                         {"role": "user", "content": "Create a histogram for all of the netid OUIs"},
                         {"role": "assistant",
                          "content": "<functioncall>\n{\n    \"name\": \"execute_python\",\n    \"arguments\": {\n        \"code\": {\"code\":\"import pandas as pd\\nimport matplotlib.pyplot as plt\\n\\n# Load data from JSON file\\nfile_path = './data/WiGLE.json'\\ndata = pd.read_json(file_path)\\n\\n# Extract the OUI (first 8 characters of netid)\\ndata['OUI'] = data['netid'].str[:8]\\n\\n# Plot histogram\\nplt.figure(figsize=(10, 6))\\ndata['OUI'].value_counts().plot(kind='bar')\\nplt.title('Histogram of NetID OUIs')\\nplt.xlabel('OUI')\\nplt.ylabel('Frequency')\\nplt.show()\"}\n    }\n}\n</functioncall>\n"},
                         {"role": "tool", "tool_call_id": "call_0oiQmRKvKAZAoXRFPpXE7gp5", "name": "execute_python",
                          "content": "Figure(1000x600)\nAxes(0.125,0.11;0.775x0.77)\nText(0.5, 1.0, 'Histogram of NetID OUIs')\nText(0.5, 0, 'OUI')\nText(0, 0.5, 'Frequency')\n"},
                         {"role": "assistant",
                          "content": "Here is the histogram showing the distribution of the first 8 characters of the `netid` (OUI) from the dataset. Each bar represents the frequency of a specific OUI in the data."}]}
json_str = json.dumps(messages)
result = json.loads(json_str)

# Global variables
selected_node = None
node_positions = {}
current_annotation = None
tree = create_sample_tree()
depth = 3  # manually set the depth of the tree
step_x = 2.5  # horizontal spacing between nodes
step_y = 2.0  # vertical spacing between levels

# Create the Tkinter window
root = tk.Tk()
root.title("Tree Visualizer")

# Create a Matplotlib figure and axis
fig = Figure(figsize=(8, 6))
ax = fig.add_subplot(111)
ax.set_title('Tree Structure Viewer')
ax.set_xlim(-10, 10)
ax.set_ylim(-2, depth * step_y + 2)
ax.axis('off')

# Plot the initial tree
plot_tree(ax, tree, 0, depth * step_y, step_x, step_y)

# Create a FigureCanvasTkAgg widget to embed the plot in Tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Create a frame for the controls
control_frame = tk.Frame(root, width=400, height=500) # the size of the component that holds the text for each node
control_frame.pack_propagate(False)
control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

add_button = tk.Button(control_frame, text="Branch from this node", command=branch_from_node)
add_button.pack(pady=5)

add_button = tk.Button(control_frame, text="Jump into this conversation", command=jump_into_convo)
add_button.pack(pady=5)

# Create a frame for the scrollable text widget
text_frame = tk.Frame(control_frame)
text_frame.pack(fill=tk.BOTH, expand=True)

# Create a scrollbar
scrollbar = tk.Scrollbar(text_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Create a text widget with a scrollbar
text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Configure the scrollbar
scrollbar.config(command=text_widget.yview)

# Add static text to the text widget
text_widget.insert(tk.END, "Click on a node to select it and enter a child node name.")
text_widget.config(state=tk.DISABLED)

# Create and pack the Matplotlib navigation toolbar in the control frame
toolbar = NavigationToolbar2Tk(canvas, control_frame)
toolbar.update()
toolbar.pack(side=tk.TOP, fill=tk.X)

# Register click event handler for the Matplotlib plot
fig.canvas.mpl_connect('button_press_event', on_node_click)

# Start the Tkinter main loop
root.mainloop()
