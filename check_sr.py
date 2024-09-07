import requests
from requests.auth import HTTPBasicAuth
import pdfplumber
import re

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

sr_username = "prakash.iyengar@kyndryl.com"
sr_password = "Rp.BUYJD+jvaE(kkA32fz97-=!myHZode{U{9sskhI110Q(uj6PXaa{ku?>dQ}w6"

pdf_path = 'Data/Other/sr_create_info.pdf'

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def parse_text_to_dict(text):
    # Initialize dictionaries
    aiops_dict = {}
    extension_dict = {}
    automation_service_dict = {}

    # Split text into sections based on known patterns
    sections = text.split('Information required to create a sr or service request in servicenow to ')
    cleaned_data_list = [data.replace('\n', ' ') for data in sections]
    # print(cleaned_data_list)
    for section in cleaned_data_list:
        # Remove any extraneous whitespace and bullet points
        section = section.replace('\uf0b7', '').strip()

        # Check and parse sections based on known headers
        if "AIOPS" in section:
            lines = section.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split('AIOPS', 1)
                    aiops_dict["AIOPS"] = value.strip()

        elif "enable extension services" in section:
            lines = section.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split('enable extension services', 1)
                    extension_dict["extension service"] = value.strip()

        elif "enable Automation services" in section:
            lines = section.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split('enable Automation services', 1)
                    automation_service_dict["automation service"] = value.strip()

    return aiops_dict, extension_dict, automation_service_dict

def check_sr(sr_num):
  # sr_url = f"https://kdusdemo5.service-now.com/api/now/table/sc_req_item?sysparm_query=number={sr_num}"
  sr_url = f"https://kdusdemo5.service-now.com/api/now/table/sc_req_item?sysparm_query=number={sr_num}&sysparm_display_value=true&sysparm_limit=1"

  # Set headers
  headers = {
      "Accept": "application/json"
  }

  # Make the GET request to ServiceNow API
  response = requests.get(sr_url, auth=HTTPBasicAuth(sr_username, sr_password), headers=headers, verify=False)

  # Check if the request was successful
  if response.status_code == 200:
      # Parse the JSON response
      data = response.json()
      ritm_check_response = "ServiceNow RITM Task Data retrieved successfully"
      item = data['result'][0]
      short_description = item.get('short_description', 'No description provided')
      state = item.get('state', 'No state provided')
      opened_at = item.get('opened_at', 'No opened date provided')
      due_date = item.get('due_date', 'No due date provided')
      assigned_to = item.get('assigned_to', {}).get('link', 'No assigned user provided')
      worknote_update = item.get('work_notes', 'No update')

      if worknote_update != 'No update':
        pattern1 = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - [\w\s]+ \(Work notes\)\s+.*?)(?=\n\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - |$)'
        pattern2 = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'

        match = re.search(pattern1, worknote_update, re.DOTALL)  # re.DOTALL allows '.' to match newline characters

        if match:
            result = match.group(1).replace('\n', ' ')  # Replace newlines with spaces to make it single line

            last_wn_updateon = result.split(' - ')[0]

            split_text = re.split(pattern2, worknote_update)
            for idx, segment in enumerate(split_text):
                if idx == 1:
                    worknote_update_info = segment.strip()
                    segment1 = segment.split('\n')

                    filtered_segment1 = [item for item in segment1 if item.strip()]

                    username_pattern = r'- (.*) \(Work notes\)'
                    un_match = re.search(username_pattern, filtered_segment1[0])
                    last_wn_updatedby = un_match.group(1)
                    last_wn_update = filtered_segment1[-1]

                    # print("######################## filtered_segment1 ########################\n\n\n")
                    # print(f"Last updated on {last_wn_updateon}")
                    # print(f"Last updated by {last_wn_updatedby}")
                    # print(f"Last update {last_wn_update}")
                    # print("\n\n\n######################## filtered_segment1 ########################")
                    break
            worknote_update_info = f"{last_wn_update} and it was updated on {last_wn_updateon} by {last_wn_updatedby}"
        else:
            worknote_update_info = "No Worknote update found"

      #check_sr_dict = {'ritm_check_response': ritm_check_response, 'ritm_number':item.get('number', 'N/A'),'ritm_description':short_description,'ritm_state':state,'ritm_opened_at':opened_at,'ritm_due_date':due_date,'ritm_assined_to':assigned_to,'worknote_update_info':worknote_update_info}
      check_sr_dict = {'ritm_check_response': ritm_check_response, 'ritm_number':item.get('number', 'N/A'),'ritm_description':short_description,'ritm_state':state,'ritm_opened_at':opened_at,'ritm_due_date':due_date,'worknote_update_info':worknote_update_info}
  else:
      check_sr_dict = {'ritm_check_response': f"Failed to retrieve data. Status code: {response.status_code}, Response: {response.text}"}

  # print(check_sr_dict)
  return check_sr_dict

def create_sr(short_description):
  # API endpoint for creating SC_Task
  api_endpoint = "/api/now/table/sc_req_item"
  instance_url = "https://kdusdemo5.service-now.com"

  pdf_text = extract_text_from_pdf(pdf_path)
  aiops_dict, extension_dict, automation_service_dict = parse_text_to_dict(pdf_text)

  if ('extension service' in short_description.lower()):
      request_short_description = short_description
      request_description = extension_dict["extension service"]

  elif ('aiops' in short_description.lower()):
      request_short_description = short_description
      request_description = aiops_dict["AIOPS"]

  elif ('automation service' in short_description.lower()):
      request_short_description = short_description
      request_description = aiops_dict["automation service"]

  else:
      request_short_description = short_description
      request_description = short_description

  # Full URL for the API request
  post_api_url = f"{instance_url}{api_endpoint}"
  # Data to be sent in the API request
  data = {
      "short_description": request_short_description,
      "description": request_description
  }

  # Make the API request
  response = requests.post(
      post_api_url,
      auth=HTTPBasicAuth(sr_username, sr_password),
      headers={"Content-Type": "application/json", "Accept": "application/json"},
      json=data
  )

  # Check if the request was successful
  if response.status_code == 201:
      ritm_creation_response = "RITM Task created successfully!"

      data = response.json()
      ritm_number = data['result'].get('number', 'Not Available')
      ritm_creation_date = data['result'].get('sys_created_on', 'Not Available')
      ritm_state = data['result'].get('state', 'Not Available')
      ritm_created_by = data['result'].get('sys_created_by', 'Not Available')
      ritm_short_description = data['result'].get('short_description', 'Not Available')
      ritm_description = data['result'].get('description', 'Not Available')

      create_sr_dict = {'ritm_creation_response': ritm_creation_response, 'ritm_number':ritm_number, 'ritm_creation_date':ritm_creation_date, 'ritm_current_state': ritm_state, 'ritm_created_by': ritm_created_by, 'ritm_short_description': ritm_short_description, 'ritm_description': ritm_description}

  else:
      ritm_creation_response = "Failed to create RITM Task"
      create_sr_dict = {'ritm_creation_response': ritm_creation_response}
  return create_sr_dict