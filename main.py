import tkinter as tk
import json
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage, ToolCall, BaseMessage

# Highlight current convo you are in

# Define the Node class
class Node:
    def __init__(self, message, parent=None):
        self.parent = parent
        self.message = message
        self.children = []


# Function to traverse up the tree and convert the messages to json
def messages_to_json(is_leaf=False):
    global selected_node

    if selected_node is not None:
        current_node = selected_node
        stack = []  # Stack of dictionaries of messages

        # Goes through all the nodes up to the root and puts their info in correct order into stack
        while current_node is not None:
            # Add tool-specific fields if the role is "tool"
            message = {
                "role": current_node.message.type,
                "content": current_node.message.content
            }

            # We want AI to generate its response
            if stack == [] and current_node.message.type == 'assistant' and is_leaf is False:
                continue  # If wanting to regen AI response, skip generating the node unless its a leaf node

            stack.append(message)
            current_node = current_node.parent

        stack.reverse()

        result = {"messages": stack}

        return json.dumps(result)


def save_tree():
    print('saved tree')


# Function to handle adding a child node
def branch_from_node():
    global selected_node, ax, tree, canvas

    if selected_node is not None:
        if selected_node.children != []: # Cannot branch from a leaf node
            new_node = Node(BaseMessage(content='placeholder content', type=selected_node.children[0].message.type), selected_node)
            selected_node.children.append(new_node)

            # Clear and redraw plot
            ax.clear()
            ax.set_xlim(-10, 10)
            ax.set_ylim(-4, depth * step_y + 2)
            ax.axis('on')

            plot_tree(ax, tree, 0, depth * step_y, step_x, step_y)
            canvas.draw()
            print(messages_to_json())
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
                text_widget.insert(tk.END, f"Selected Node: {node.message.type}\n\n{node.message.content}")
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
    if node.message.type == 'system':
        ax.text(x, y, 'system', bbox=dict(facecolor='#ffffff', alpha=1), ha='center', va='center', fontsize=12)
    elif node.message.type == 'user':
        ax.text(x, y, 'user', bbox=dict(facecolor='#aaa', alpha=1), ha='center', va='center', fontsize=12)
    elif node.message.type == 'assistant':
        ax.text(x, y, 'assistant', bbox=dict(facecolor='#97dcfc', alpha=1), ha='center', va='center', fontsize=12)
    elif node.message.type == 'tool':
        ax.text(x, y, 'tool', bbox=dict(facecolor='#97fca1', alpha=1), ha='center', va='center', fontsize=12)

    node_positions[node] = (x, y)

    # Calculate positions for children
    if len(node.children) > 0:
        child_spacing = step_x * (len(node.children) - 1) / 2
        for i, child in enumerate(node.children):
            plot_tree(ax, child, x - child_spacing + i * step_x, y - step_y, step_x, step_y)
            ax.plot([x, x - child_spacing + i * step_x], [y, y - step_y], 'k-')

# Sample tree structure
def create_tree():
    base_message = BaseMessage(type='system', content=result['messages'][0]['content'])
    root = Node(base_message)

    youngest = root

    for message in result['messages']:
        if message['role'] == 'system':
            continue
        elif message['role'] == 'user':
            base_message = BaseMessage(type='user', content=message['content'])
            new_node = Node(base_message, youngest)
        elif message['role'] == 'assistant':
            base_message = BaseMessage(type='assistant', content=message['content'])
            new_node = Node(base_message, youngest)
        elif message['role'] == 'tool':
            base_message = BaseMessage(type='tool', content=message['content'])
            new_node = Node(base_message, youngest)

        youngest.children = [new_node]
        youngest = new_node

    return root

# Load and parse the JSON
messages = {"messages": [
        {
            "content": "You are a helpful assistant with access to the following functions. Use them if required -\n{\n    \"type\": \"function\",\n    \"function\": {\n        \"name\": \"execute_python\",\n        \"description\": \"Run a command in a python interpreter\",\n        \"parameters\": {\n            \"type\": \"object\",\n            \"properties\": {\n                \"code\": {\n                    \"type\": \"string\",\n                    \"description\": \"Python code to execute\",\n                }\n            },\n            \"required\": [\"code\"],\n        }\n    }\n}\n                \nTo use these functions respond with:\n<functioncall>\n{\n    \"name\": \"function_name\",\n    \"arguments\": {\n        \"arg_1\": \"value_1\",\n        \"arg_1\": \"value_1\",\n        ...\n    }\n}\n</functioncall>\n\nEdge cases you must handle:\n- If there are no functions that match the user request, you will respond politely that you cannot help.\n\nThe data is found in /tmp/xPdsFYju.kismet\n",
            "role": "system"
        },
        {
            "content": "What devices was responsible for the greatest number of the captured packets?",
            "role": "user"
        },
        {
            "content": "<functioncall>\n{\n    \"name\": \"execute_python\",\n    \"arguments\": {\n        \"code\": \"import sqlite3\nimport pandas as pd\n\n# Connect to the SQLite database\nconn = sqlite3.connect('/tmp/xPdsFYju.kismet')\n\n# Load packets table into a pandas DataFrame\npackets_df = pd.read_sql_query('SELECT * FROM packets', conn)\n\n# Count the number of packets per device (using devkey)\npacket_counts = packets_df['devkey'].value_counts()\n\n# Find the device responsible for the greatest number of packets\nmost_packets_device = packet_counts.idxmax()\nmost_packets_device\"\n    }\n}\n</functioncall>",
            "role": "assistant"
        },
        {
            "content": "0\n",
            "role": "tool"
        },
        {
            "content": "<functioncall>\n{\n    \"name\": \"execute_python\",\n    \"arguments\": {\n        \"code\": \"# Display the packet counts for all devices\npacket_counts\"\n    }\n}\n</functioncall>",
            "role": "assistant"
        },
        {
            "content": "devkey\n0    335113\nName: count, dtype: int64\n",
            "role": "tool"
        },
        {
            "content": "<functioncall>\n{\n    \"name\": \"execute_python\",\n    \"arguments\": {\n        \"code\": \"# Count the number of packets per source MAC address\nsource_mac_counts = packets_df['sourcemac'].value_counts()\n\n# Count the number of packets per destination MAC address\ndest_mac_counts = packets_df['destmac'].value_counts()\n\nsource_mac_counts, dest_mac_counts\"\n    }\n}\n</functioncall>",
            "role": "assistant"
        },
        {
            "content": "(sourcemac\nE0:C2:64:C0:B0:66    8365\nD0:21:F9:B3:0E:B1    7702\n00:E0:4C:97:61:3F    6727\nD2:21:F9:A3:01:BB    5885\nD2:21:F9:A3:01:BA    5499\n                     ... \nD6:F2:70:74:CC:7C       1\nE8:B5:D0:74:40:83       1\nAE:03:49:EB:52:E9       1\n2C:DC:D7:17:1E:E1       1\n3C:BD:C5:F0:4C:A3       1\nName: count, Length: 11714, dtype: int64, destmac\nFF:FF:FF:FF:FF:FF    130492\nE0:C2:64:C0:B0:66      6637\nD2:21:F9:A3:01:BB      5659\n68:72:51:3E:69:A4      5255\n00:E0:4C:97:61:3F      5246\n                      ...  \n56:7D:4D:15:5D:B5         1\n74:75:48:29:26:9C         1\nD6:6D:0E:E5:37:D5         1\n18:78:D4:35:86:82         1\n20:D7:78:93:90:53         1\nName: count, Length: 7825, dtype: int64)\n",
            "role": "tool"
        },
        {
            "content": "Here are the results for the source and destination MAC addresses with the highest packet counts:\n\n### Source MAC Addresses\n1. **E0:C2:64:C0:B0:66**: 8365 packets\n2. **D0:21:F9:B3:0E:B1**: 7702 packets\n3. **00:E0:4C:97:61:3F**: 6727 packets\n4. **D2:21:F9:A3:01:BB**: 5885 packets\n5. **D2:21:F9:A3:01:BA**: 5499 packets\n\n### Destination MAC Addresses\n1. **FF:FF:FF:FF:FF:FF** (Broadcast): 130492 packets\n2. **E0:C2:64:C0:B0:66**: 6637 packets\n3. **D2:21:F9:A3:01:BB**: 5659 packets\n4. **68:72:51:3E:69:A4**: 5255 packets\n5. **00:E0:4C:97:61:3F**: 5246 packets\n\nThe broadcast address `FF:FF:FF:FF:FF:FF` has the highest number of packets as the destination, which is expected in network traffic.\n\nThe MAC address **E0:C2:64:C0:B0:66** appears prominently as both a source and destination, indicating it is likely responsible for a significant portion of the captured packets.\n\nWould you like to investigate this specific device further or perform another analysis?",
            "role": "assistant"
        },
        {
            "content": "Tell me more about E0:C2:64:C0:B0:66",
            "role": "user"
        },
        {
            "content": "<functioncall>\n{\n    \"name\": \"execute_python\",\n    \"arguments\": {\n        \"code\": \"# Query the devices table for information about the device with MAC address E0:C2:64:C0:B0:66\nquery = '''\nSELECT * FROM devices WHERE devmac = 'E0:C2:64:C0:B0:66'\n'''\ndevice_info = pd.read_sql_query(query, conn)\ndevice_info\"\n    }\n}\n</functioncall>",
            "role": "assistant"
        },
        {
            "content": "   first_time   last_time                         devkey  ... bytes_data      type                                             device\n0  1718034753  1718037106  4202770D00000000_66B0C064C2E0  ...     230981  Wi-Fi AP  b'{\"kismet.device.base.first_time\": 1718034753...\n\n[1 rows x 15 columns]\n",
            "role": "tool"
        },
        {
            "content": "Here's the information about the device with MAC address **E0:C2:64:C0:B0:66**:\n\n| Column           | Value                                         |\n|------------------|-----------------------------------------------|\n| first_time       | 1718034753                                    |\n| last_time        | 1718037106                                    |\n| devkey           | 4202770D00000000_66B0C064C2E0                 |\n| phyname          | IEEE802.11                                    |\n| devmac           | E0:C2:64:C0:B0:66                             |\n| strongest_signal | -55                                           |\n| min_lat          | 39.130661                                     |\n| min_lon          | -76.809962                                    |\n| max_lat          | 39.131397                                     |\n| max_lon          | -76.809777                                    |\n| avg_lat          | 39.130888                                     |\n| avg_lon          | -76.809874                                    |\n| bytes_data       | 230981                                        |\n| type             | Wi-Fi AP                                      |\n| device           | (JSON blob with detailed device information)  |\n\nThe device is a Wi-Fi Access Point (AP) with the following characteristics:\n- **First Seen**: Timestamp 1718034753\n- **Last Seen**: Timestamp 1718037106\n- **Strongest Signal**: -55 dBm\n- **Location**: \n  - Minimum Latitude: 39.130661\n  - Minimum Longitude: -76.809962\n  - Maximum Latitude: 39.131397\n  - Maximum Longitude: -76.809777\n  - Average Latitude: 39.130888\n  - Average Longitude: -76.809874\n- **Bytes of Data**: 230981 bytes\n\nThe `device` column contains a JSON blob with detailed device information. Would you like to extract and analyze the contents of this JSON blob?",
            "role": "assistant"
        }
    ]
}

json_str = json.dumps(messages)
result = json.loads(json_str)

# Global variables
selected_node = None
node_positions = {}
current_annotation = None
tree = create_tree()
depth = len(result['messages']) / 2  # manually set the depth of the tree
step_x = 3.5  # horizontal spacing between nodes
step_y = 1.0  # vertical spacing between levels

# Create the Tkinter window
root = tk.Tk()
root.title("Tree Visualizer")

# Create a Matplotlib figure and axis
fig = Figure(figsize=(8, 6))
ax = fig.add_subplot(111) # Used 111 originially but dk what it does
fig.subplots_adjust(left=0, right=1, top=1, bottom=0) # Makes the plot cover the entire canvas
ax.set_title('Tree Structure Viewer')
ax.set_xlim(-10, 10)
ax.set_ylim(-4, depth * step_y + 2)
ax.axis('on')

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
