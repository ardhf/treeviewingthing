import tkinter as tk
import json
import sample_data
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage, ToolCall, BaseMessage


# TODO: Highlight current convo you are in
# TODO: Make zooming work with mouse
# TODO: Fix hitboxes of messages in plot
# TODO: Make messages fit on screen and make it look nice
# TODO: Export the tree to save and come back to

# Teddy ideas
# TODO: Make chatlog like ChatGPT and button to open graph
# TODO: hide graph by default
# TODO: add a textbox at the bottom of left panel to talk to LLM
# TODO: When clicking on a node, load all of the conversation up to that point into the window

# ends when AI talks and does not call tool, either user input or end


# message: a langchain BaseMessage with the type(aka role) and content parameters
# parent: parent node
class Node:
    def __init__(self, message, parent=None):
        self.parent = parent
        self.message = message
        self.children = []


# Function to take your current node and follow its parents up to root to give you the correct branched conversation
# is_leaf: if the selected node is a leaf node
def messages_to_json(is_leaf=False):
    global selected_node

    if selected_node is not None:
        current_node = selected_node
        stack = []  # Stack for dictionaries of messages

        # Goes through all the nodes up to the root and puts their info in correct order into stack
        while current_node is not None:
            message = {
                "role": current_node.message.type,
                "content": current_node.message.content
            }

            # If we branch into a new Assistant node, we want to not append it so the LLM can generate its own response
            if stack == [] and current_node.message.type == 'assistant' and is_leaf is False:
                current_node = current_node.parent
                continue

            stack.append(message)
            current_node = current_node.parent

        stack.reverse()  # puts the messages in the correct top down order

        result = {"messages": stack}

        return json.dumps(result)  # Converts to a json


def save_tree():
    print('saved tree')  # totally saves the tree and doesn't just print to console


# Function to handle adding a child node
def branch_from_node():
    global selected_node, ax, tree, canvas

    if selected_node is not None:
        if selected_node.children != []:  # Cannot branch from a leaf node
            new_node = Node(BaseMessage(content='placeholder content', type=selected_node.children[0].message.type), selected_node)
            selected_node.children.append(new_node)

            # Clear and redraw plot
            plot_options()
            canvas.draw()
            print(messages_to_json())  # Current convo in JSON form
        else:
            print('Not allowed to branch from a leaf node, jumping into conversation instead')
            print(messages_to_json(is_leaf=True))

# Function to handle node click event
def on_node_click(event):
    global selected_node, current_annotation, text_widget
    if event.inaxes is not None:
        # Clear existing annotation if present
        if current_annotation:
            current_annotation.remove()
            current_annotation = None

        for node, (x, y) in node_positions.items():
            if abs(event.xdata - x) < 0.4 and abs(event.ydata - y) < 0.4:
                selected_node = node
                context_menu(event)
                # Update text widget with information about the clicked node
                text_widget.config(state=tk.NORMAL)
                text_widget.delete('1.0', tk.END)
                text_widget.insert(tk.END, f"Selected Node: {node.message.type}\n\ntool_call_id: {node.message.id}\n\ncontent: {node.message.content}")
                text_widget.config(state=tk.DISABLED)
                break

# Function to show context menu for creating a child node
def context_menu(event):
    global selected_node, current_annotation

    if selected_node is not None:
        current_annotation = ax.annotate(
            "Selected Node",
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

    # Different roles have different colors
    match node.message.type:
        case 'system':
            color = '#fff'
        case 'user':
            color = '#aaa'
        case 'assistant':
            color = '#97dcfc'
        case 'tool':
            color = '#97fca1'

    ax.text(x, y, node.message.type, bbox=dict(facecolor=color, alpha=1, ec='black', boxstyle='round,pad=0.5'), ha='center', va='center', fontsize=12)

    node_positions[node] = (x, y)  # Global array of coords for all node positions

    # Calculate positions for children
    if len(node.children) > 0:
        child_spacing = step_x * (len(node.children) - 1) / 2
        for i, child in enumerate(node.children):
            plot_tree(ax, child, x - child_spacing + i * step_x, y - step_y, step_x, step_y)
            ax.plot([x, x - child_spacing + i * step_x], [y, y - step_y], 'k-')

# Want to take in a list of langchain messages and turn it into a tree
def create_tree():
    # All conversations start with a system node and there can only be one
    base_message = BaseMessage(type='system', content=result['messages'][0]['content'])
    root = Node(base_message)

    youngest = root

    for message in result['messages'][1:]:  # Skips the first element because its the root node system message
        base_message = BaseMessage(type=message['role'], content=message['content'])
        new_node = Node(base_message, youngest)
        youngest.children = [new_node]
        youngest = new_node

    return root


def plot_options():
    ax.clear()
    ax.set_xlim(-10, 10)
    ax.set_ylim(-4, depth * step_y + 2)

    # Plot the initial tree
    plot_tree(ax, tree, 0, depth * step_y + 1, step_x, step_y)


# Only used for testing
# Converts a specified string of JSON into {"messages": x} where x is a list of langchain messages
def json_to_messages(json_messages):
    list_of_messages = []
    result = json_messages
    system_msg = SystemMessage(content=result['messages'][0]['content'])
    list_of_messages.append(system_msg)

    for message in result['messages'][1:]:
        match message['role']:
            case 'user':
                curr_message = HumanMessage(content=message['content'])
            case 'assistant':
                # Checks if the AI message has tool calls
                if 'tool_calls' in message:
                    tool_prefix = message['tool_calls'][0]  # Makes the long json key lookup not look as ugly

                    msg_tool_call = ToolCall(
                        name=tool_prefix['tool_call']['name'],
                        args=tool_prefix['tool_call']['arguments'],
                        id=tool_prefix['id'])

                    curr_message = AIMessage(content=message['content'], tool_calls=[msg_tool_call])
                else:
                    curr_message = AIMessage(content=message['content'])
            case 'tool':
                curr_message = ToolMessage(content=message['content'], tool_call_id=message['tool_call_id'], type=message['role'], name=message['name'])

        list_of_messages.append(curr_message)

    return list_of_messages


result = sample_data.conversation1  # Loads the first sample convo

# Global variables
selected_node = None
node_positions = {}
current_annotation = None

(json_to_messages(sample_data.conversation1))

tree = create_tree()

depth = len(result['messages']) / 1.5  # manually set the depth of the tree
step_x = 3.5  # horizontal spacing between nodes
step_y = 1.0  # vertical spacing between levels

# Create the Tkinter window
root = tk.Tk()
root.title("Tree Visualizer")

# Create a Matplotlib figure and axis
fig = Figure(figsize=(8, 6))
ax = fig.add_subplot(111)  # 1 row, 1 col, 1st index
fig.subplots_adjust(left=0, right=1, top=1, bottom=0) # Makes the plot cover the entire canvas

# Calls some shared config options about the plot
plot_options()

# Create a FigureCanvasTkAgg widget to embed the plot in Tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Create a frame for the controls (left side)
control_frame = tk.Frame(root, width=400, height=500) # the size of the component that holds the text for each node
control_frame.pack_propagate(False)  # Text inside does not cause text container to go wild
control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)  # Anchor left, fill Y, and add padding in x and y

# Create the buttons on the top left
tk.Button(control_frame, text="Branch from this node", command=branch_from_node).pack(pady=5)
tk.Button(control_frame, text="Save Tree", command=save_tree).pack(pady=5)

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

# Create and pack the Matplotlib navigation toolbar in the control frame
toolbar = NavigationToolbar2Tk(canvas, control_frame)
toolbar.update()
toolbar.pack(side=tk.TOP, fill=tk.X)

# Register click event handler for the Matplotlib plot
fig.canvas.mpl_connect('button_press_event', on_node_click)

# Start the Tkinter main loop
root.mainloop()
