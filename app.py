from flask import Flask, render_template, request
import requests, os, time
import markdown

app = Flask(__name__)

# 🔐 API KEY (set properly before running)
os.environ["OPENROUTER_API_KEY"] = "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"

def call_llm(model, prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4
    }

    r = requests.post(url, headers=headers, json=data)
    response = r.json()

    # 🔴 Handle API errors
    if "error" in response:
        return f"API Error ({model}): {response['error'].get('message', 'Unknown error')}"

    # 🔴 Handle unexpected response
    if "choices" not in response:
        return f"Unexpected response from {model}: {response}"

    return response["choices"][0]["message"]["content"]

expert_models = {
    "fever_expert": "deepseek/deepseek-chat",
    "symptom_expert": "qwen/qwen-2.5-7b-instruct",
    "disease_expert": "meta-llama/llama-3-8b-instruct",
    "diagnosis_expert": "mistralai/mistral-7b-instruct",
    "drug_expert": "mistralai/mistral-nemo",
    "lab_expert": "openai/gpt-4o-mini",
    "risk_expert": "anthropic/claude-3.5-haiku"
}

expert_prompts = {
    "fever_expert": "Evaluate fever using WHO & CDC guidelines.",
    "symptom_expert": "Analyze symptoms using PubMed & Medline.",
    "disease_expert": "Match symptoms with diseases using Mayo Clinic.",
    "diagnosis_expert": "Evaluate diagnosis likelihood using clinical rules.",
    "drug_expert": "Suggest treatment with FDA guidance.",
    "lab_expert": "Interpret lab tests using NIH references.",
    "risk_expert": "Estimate risk & red flags using NICE guidelines."
}

def run_pipeline(user_input):
    outputs = {}

    for expert, model in expert_models.items():
        prompt = f"{expert_prompts[expert]}\n\nPatient Case:\n{user_input}"
        outputs[expert] = call_llm(model, prompt)
        time.sleep(1)

    combined_report = ""
    for k, v in outputs.items():
        combined_report += f"{k.upper()}:\n{v}\n\n"

    final_prompt = f"""
    You are a medical consensus engine.
    Generate final output with:
    - Diagnosis likelihood
    - Evidence
    - Red flags
    - Recommendations

    Report:
    {combined_report}
    """

    final_text = call_llm("deepseek/deepseek-chat", final_prompt)

    # ❌ Remove unwanted follow-up question
    unwanted_phrases = [
    "Would you like",
    "Do you want",
    "Can I help",
    "locating nearby clinics",
    "travel health resources",
    "Would you like assistance",
    "Would you like guidance",
    "Let me know if"
]

    lines = final_text.splitlines()

    clean_lines = []
    for line in lines:
        lower = line.lower()
        if any(phrase.lower() in lower for phrase in unwanted_phrases):
            continue
        clean_lines.append(line)

    final_text = "\n".join(clean_lines)

    # ✅ Convert Markdown → HTML
    final_html = markdown.markdown(final_text)

    return final_html

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        symptoms = request.form["symptoms"]
        result = run_pipeline(symptoms)
        return render_template("result.html", result=result)

    return render_template("index.html")

# if __name__ == "__main__":
#     app.run(debug=True)
