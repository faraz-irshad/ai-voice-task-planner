def schedule_task(priority):
    if priority in ["Urgent & Important", "Urgent & Not Important"]:
        return "Today"
    elif priority == "Important & Not Urgent":
        return "Tomorrow"
    else:
        return "Later"

def create_focus_blocks(tasks):
    deep = [t for t in tasks if t.get("type") == "Deep Task"]
    micro = [t for t in tasks if t.get("type") == "Micro Task"]
    other = [t for t in tasks if t.get("type") == "Other"]
    
    blocks = []
    for task in deep:
        blocks.append({"type": "Deep Task", "tasks": [task]})
    
    for i in range(0, len(micro), 5):
        blocks.append({"type": "Micro Tasks", "tasks": micro[i:i+5]})
    
    if other:
        blocks.append({"type": "Other", "tasks": other})
    
    return blocks
