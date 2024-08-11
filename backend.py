#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint
from flask import Flask, request, jsonify
from PIL import Image
import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
import os
import io

app = Flask(__name__)

server_address = "comfyui:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    #stores prompt in dictionary and encodes it to bytes
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    #Creates a post request to comfyui server
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    #Sends request and returns response from server
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    #defines a data type for an image
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    #encodes image data type to bytes
    url_values = urllib.parse.urlencode(data)
    #gets image from comfyui server matching bytecode description
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    #fetches history of prompt execution given a prompt id
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    #sends prompt to server, returns prompt id
    prompt_id = queue_prompt(prompt)['prompt_id']
    #empty buffer to store images
    output_images = {}
    while True:
        #listens to websocket responses, stop listening when execution is complete
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            continue #previews are binary data
    
    history = get_history(prompt_id)[prompt_id]
    #iterates through the history data to find image outputs from nodes, stores bytecode in output images
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images


def get_and_save_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
        else:
            continue  # Previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if 'images' in node_output:
            images_output = []
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                # Save the image
                image_path = f"output/{node_id}_{image['filename']}.png"
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                images_output.append(image_path)
            output_images[node_id] = images_output

    return output_images





@app.route('/execute', methods=['POST'])
def execute_workflow():
    #gets data from post request and populates variables
    data = request.get_json()
    positive_prompt = data.get('positive_prompt', '')
    negative_prompt = data.get('negative_prompt', '')
    ksampler_seed = data.get('ksampler_seed', 1)
    #edits the workflow json file
    with open("workflow_gordon_api.json", "r", encoding="utf-8") as f:
        workflow_data = f.read()

    prompt = json.loads(workflow_data)
    prompt["6"]["inputs"]["text"] = positive_prompt
    prompt["7"]["inputs"]["text"] = negative_prompt
    prompt["3"]["inputs"]["seed"] = ksampler_seed
    #connect to websocket and execute main function
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    #images = get_images(ws, prompt)
    images = get_and_save_images(ws,prompt)

    for node_id, paths in images.items():
        for path in paths:
            img = Image.open(path)
            img.show()

    return jsonify({"images": images})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)