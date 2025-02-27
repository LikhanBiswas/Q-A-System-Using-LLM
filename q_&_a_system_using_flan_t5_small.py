# -*- coding: utf-8 -*-
"""Q & A system using flan-t5-small.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/10xHpr7015KPTBkQo8dqOZanY1Yun9Vev
"""

# [ Start ]
#    |
#    v
# +------------------+
# |  Load CSV Data   |
# +------------------+
#           |
#           v
# +-----------------------+
# |   Data Preprocessing  |
# | - Combine columns     |
# |   into text sentences |
# +-----------------------+
#           |
#           v
# +-------------------------+
# | Generate Text Embeddings|
# |  using SentenceTransformer |
# +-------------------------+
#           |
#           v
# +-----------------------+
# | Build FAISS Index     |
# +-----------------------+
#           |
#           v
# +-----------------------+
# |   User Asks Question  |
# +-----------------------+
#           |
#           v
# +-----------------------+
# | Convert Question to   |
# |  Embedding            |
# +-----------------------+
#           |
#           v
# +-----------------------+
# | Retrieve Relevant     |
# |    Contexts           |
# |  from FAISS Index     |
# +-----------------------+
#           |
#           v
# +-----------------------+
# |   Create Prompt for   |
# |      FLAN-T5          |
# +-----------------------+
#           |
#           v
# +-----------------------+
# | Generate Answer with  |
# |      FLAN-T5          |
# +-----------------------+
#           |
#           v
# +-----------------------+
# |   Display Answer to   |
# |       the User        |
# +-----------------------+
#           |
#          [End]

!pip install transformers sentence-transformers
!pip install faiss-cpu
!pip install gradio
!pip install pandas

from google.colab import files

uploaded = files.upload()

import pandas as pd

# Load the data
df = pd.read_csv('football_data.csv')
df.head()

# Data Preprocessing
df['score'] = df['score'].str.replace(' ', '')
df[['home_goals', 'away_goals']] = df['score'].str.split('-', expand=True)
df['home_goals'] = df['home_goals'].astype(int)
df['away_goals'] = df['away_goals'].astype(int)

def get_result(row):
    if row['home_goals'] > row['away_goals']:
        return 'Home Win'
    elif row['home_goals'] < row['away_goals']:
        return 'Away Win'
    else:
        return 'Draw'

df['result'] = df.apply(get_result, axis=1)

df['text'] = df.apply(
    lambda row: (f"On {row['date']}, {row['home_team']} played against {row['away_team']} with a score of "
                 f"{row['score']}, resulting in a {row['result']}."),
    axis=1
)

from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Regenerate Embeddings
import faiss
import numpy as np
embeddings = embedding_model.encode(df['text'].tolist())
embedding_dim = embeddings.shape[1]
index = faiss.IndexFlatL2(embedding_dim)
index.add(np.array(embeddings))

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
model_name = 'google/flan-t5-small'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def retrieve_context(question, k=10):
    question_embedding = embedding_model.encode([question])
    distances, indices = index.search(np.array(question_embedding), k)
    relevant_texts = [df['text'].iloc[idx] for idx in indices[0]]
    if 'draw' in question.lower():
        relevant_texts = [text for text in relevant_texts if 'draw' in text.lower()]
    return ' '.join(relevant_texts)

def generate_answer(question):
    context = retrieve_context(question)
    if not context.strip():
        return "I'm sorry, I couldn't find any information related to your question."

    prompt = f"""You are a helpful assistant knowledgeable about football matches.

Context:
{context}

Please answer the following question based on the context provided:
{question}

Answer:"""
    inputs = tokenizer.encode(prompt, return_tensors='pt', max_length=512, truncation=True)
    outputs = model.generate(
        inputs,
        max_length=150,
        num_return_sequences=1,
        no_repeat_ngram_size=2,
        early_stopping=True
    )
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return answer.strip()

import gradio as gr
iface = gr.Interface(
    fn=generate_answer,
    inputs=gr.Textbox(lines=2, placeholder='Ask me anything about past football matches...'),
    outputs=gr.Textbox(),
    title='Football Match Q&A System using flan-t5',
    description='Ask any question about past football matches from the dataset.',
    examples=[
        "on 17-08-2024 what was the result between Arsenal and Wolves?",
        "on 17-08-2024 which team had won between Arsenal and Wolves?",
    ]
)
iface.launch(share=True)

import gradio as gr
def show_team_matches(team_name):
    matches = df[(df['home_team'] == team_name) | (df['away_team'] == team_name)]
    return matches[['date', 'home_team', 'score', 'away_team']].reset_index(drop=True)

team_iface = gr.Interface(
    fn=show_team_matches,
    inputs=gr.Textbox(placeholder='Enter a team name...'),
    outputs='dataframe',
    title='Team Match Viewer',
    description='View all matches involving a specific team.'
)

team_iface.launch(share=True)