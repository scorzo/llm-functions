import json
import requests
from openai import OpenAI
from pprint import pprint

client = OpenAI(api_key='*****')

def distill_seo_data(data):
    distilled = {}

    # Extracting essential fields
    if 'id' in data:
        distilled['siteUrl'] = data['id']

    if 'loadingExperience' in data:
        distilled['loadingExperience'] = data['loadingExperience']

    if 'lighthouseResult' in data:
        lighthouse = data['lighthouseResult']
        distilled['lighthouseResult'] = {
            'requestedUrl': lighthouse.get('requestedUrl'),
            'finalUrl': lighthouse.get('finalUrl'),
            'fetchTime': lighthouse.get('fetchTime'),
            'userAgent': lighthouse.get('userAgent')
        }

        # Extracting audit results relevant to SEO
        if 'audits' in lighthouse:
            seo_relevant_audits = [
                'first-contentful-paint',
                'speed-index',
                'largest-contentful-paint',
                'interactive',
                'cumulative-layout-shift'
            ]
            distilled['seoAudits'] = {audit: lighthouse['audits'][audit] for audit in seo_relevant_audits if audit in lighthouse['audits']}

    return distilled

def get_pagespeed_insights(url):
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        distilled_data = distill_seo_data(data)
        return distilled_data
    else:
        return {"error": "Failed to fetch data from PageSpeed Insights"}

def get_w3c_validation(url):
    api_url = f"https://validator.w3.org/nu/?doc={url}&out=json"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        distilled_data = distill_html_data(data)
        return distilled_data
    else:
        return {"error": f"Failed to fetch data from W3C Markup Validation Service. Status code: {response.status_code}"}

def distill_html_data(original_data):
    # Creating a new data structure based on the 'messages' key
    distilled_data = original_data.copy()  # Creating a shallow copy of the dictionary

    if 'messages' in distilled_data and isinstance(distilled_data['messages'], list):
        distilled_data['messages'] = distilled_data['messages'][:20]  # Reducing the 'messages' list to the first 20 items
    # If 'messages' is not a list or doesn't exist, the original data structure remains unchanged

    return distilled_data


def provide_user_specific_recommendations(analysis_type="seo"):
    if analysis_type == "seo":
        messages = [
            {"role": "system", "content": "You are an AI that returns SEO recommendations for a website."},
            {"role": "user", "content": "Analyze the SEO performance of https://myfancydomain.com"}
        ]
        function_name = "get_pagespeed_insights"
        distill_function = distill_seo_data
    elif analysis_type == "html":
        messages = [
            {"role": "system", "content": "You are an AI that returns HTML validation recommendations for a website."},
            {"role": "user", "content": "Check the HTML of https://myfancydomain.com for validation errors"}
        ]
        function_name = "get_w3c_validation"
        distill_function = distill_html_data

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0,
        functions=[
            {
                "name": "get_pagespeed_insights",
                "description": "Get Google PageSpeed Insights for a URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to analyze",
                        },
                    },
                    "required": ["url"],
                }
            },
            {
                "name": "get_w3c_validation",
                "description": "Get W3C Markup Validation Service for a URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to analyze",
                        },
                    },
                    "required": ["url"],
                }
            }
        ]
    )

    if response.choices[0].finish_reason == 'function_call':
        function_call = response.choices[0].message.function_call
        if function_call.name == "get_pagespeed_insights":
            url = json.loads(function_call.arguments)["url"]
            pagespeed_data = get_pagespeed_insights(url)

            if pagespeed_data:
                # Convert the data to a string
                data_str = json.dumps(pagespeed_data)
                data_str_pretty = json.dumps(pagespeed_data, indent=4)

                # Use GPT model to create a summary
                summary_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an AI that interprets and summarizes technical data in an easy-to-understand way."},
                        {"role": "user", "content": f"Interpret the values and explain what they mean. Make suggestions for improvement where needed by linking to pages from the support documentation located here: https://www.myfancydomain.com/support/\n{data_str}"}
                    ],
                    temperature=0.7  # Adjust as needed
                )

                summary = summary_response.choices[0].message.content
                return f"Here are some SEO recommendations:\n{summary}\n{data_str_pretty}"
            else:
                return "I couldn't generate a report."
        elif function_call.name == "get_w3c_validation":
            url = json.loads(function_call.arguments)["url"]
            w3c_data = get_w3c_validation(url)
            # pprint(w3c_data, indent=4)
            # exit()

            if w3c_data:
                # Convert the data to a string
                data_str = json.dumps(w3c_data)
                data_str_pretty = json.dumps(w3c_data, indent=4)

                # Use GPT model to create a summary
                summary_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an AI that interprets and summarizes technical data in an easy-to-understand way."},
                        {"role": "user", "content": f"Interpret the values and explain what they mean. Make suggestions for improvement where needed by linking to pages from the support documentation located here: https://www.myfancydomain.com/support/\n{data_str}"}
                    ],
                    temperature=0.7  # Adjust as needed
                )

                summary = summary_response.choices[0].message.content
                return f"Here are some W3C recommendations:\n{summary}\n{data_str_pretty}"
            else:
                return "I couldn't generate a report."

    return "I am sorry, but I could not understand your request."

if __name__ == "__main__":
    output = provide_user_specific_recommendations("seo")  # or "html"
    print(output)
