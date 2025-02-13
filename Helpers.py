import re

def extract_think_text(text):
    match = re.search(r'<think>(.*?)</think>', text, re.DOTALL)
    return match.group(1) if match else None

def split_content(text):
    match = re.search(r'<think>(.*?)</think>(.*)', text, re.DOTALL)
    if match:
        block1 = match.group(1).strip()  # Text inside <think></think>
        block2 = match.group(2).strip()  # Remaining text after </think>
        return block1, block2
    return None, text

def extract_two_sentences(text):
    # Find all sentences that start with '. ' and end with '.'
    sentences = text.split('. ')

    # Return the first two sentences or whatever is available
    return ('.'.join(sentences[1:3])).strip() + '.'

def remove_newlines(text):
    return text.replace("\n", " ").replace("\r", " ").strip()

def remove_newlines_in_latex(text):
    # Remove newlines inside LaTeX expressions (\\[ \\] or \\( \\))
    def replace_latex(match):
        # Remove newlines from LaTeX expressions and return the cleaned-up expression
        return match.group(0).replace('\n', ' ')
    
    # Regex to match LaTeX equations inside \\[ \\] or \\( \\)
    latex_regex = r"(\\\[.*?\\\]|\\(.*?\\))"
    cleaned_text = re.sub(latex_regex, replace_latex, text, flags=re.DOTALL)
    
    return cleaned_text