from model_setup import client
import json


def get_random_task_python():
    # Requesting the model to generate a random task in the same format
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": """
        Generate a random coding task for Python in the following format:
        {
            "title": "Title of the task",
            "description": "Detailed description of the task",
            "quest_languege": "Python",
            "function_template": "Function template in the following format:\ndef function_name(inputs):\n\t# Your solution here\n",
            "task_difficulty": "Task difficulty level - Based on the task difficultu could be Novice Quests, Adventerous Challenges or Epic Campaigns",
            "example_input_output": Generate exactly 10 inputs and outputs, print the inputs and outputs in arrays, each on a new line -- [
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
                {"input": "[Example input]", "output": "[Example output]"},
            ]
        }
        """}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        n=1,
        max_tokens=500,
        stop=None,
        temperature=0.7
    )
    # task = response.choices[0].to_json()['message']['content']
    task = response.choices[0].to_json()['message']['content']
    print(task)
    return str(task)


def format_task(task):
    try:
        task = task.strip()
        # Fix any common JSON formatting issues
        # task = task.replace("True", "true").replace("False", "false").replace("'", '"')
        task = json.loads(task)
        
        inputs = []
        outputs= []
        for example in task['example_input_output']:
            inputs.append(example['input'])
            outputs.append(example['output'])
        
        formatted_task = f"""
        Title: {task['title']}\n
        Description: {task['description']}\n
        Quest Language: {task['quest_language']}\n
        Function Template:\n{task['function_template']}\n
        Task Difficulty: {task['task_difficulty']}\n
        Quest Inputs:\n{inputs}\n
        Quest Outputs:\n{outputs}\n
        """
        
        # print(formatted_task)

        return formatted_task
    except Exception as e:
        print(e)
        return "Failed to format the task"
    
print(format_task(get_random_task_python()))