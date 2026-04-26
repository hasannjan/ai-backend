import json
import boto3
import urllib3
import os

# Initialize AWS S3 client
s3 = boto3.client('s3')
http = urllib3.PoolManager()

# Your backend API URL (change this!)
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://your-flask-api.com/api/execute')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'my-ai-prompts-output')

def lambda_handler(event, context):
    """
    Triggered when a file is uploaded to S3
    """
    try:
        # Step 1: Get the uploaded file details
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = event['Records'][0]['s3']['object']['key']
        
        print(f"Processing file: {file_key} from bucket: {bucket_name}")
        
        # Step 2: Read the file content from S3
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        prompt_text = response['Body'].read().decode('utf-8')
        
        print(f"Prompt content: {prompt_text[:100]}...")
        
        # Step 3: Call your Flask backend API
        payload = {
            'promptId': 1,  # You can extract this from filename or content
            'userInput': {
                'topic': prompt_text  # Or parse the prompt properly
            }
        }
        
        api_response = http.request(
            'POST',
            BACKEND_API_URL,
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        result = json.loads(api_response.data.decode('utf-8'))
        
        print(f"API Response received: {len(result.get('response', ''))} characters")
        
        # Step 4: Store the result in output S3 bucket
        output_filename = f"response_{file_key.replace('.txt', '')}.json"
        
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_filename,
            Body=json.dumps(result, indent=2),
            ContentType='application/json'
        )
        
        print(f"Response stored in: {OUTPUT_BUCKET}/{output_filename}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing complete',
                'input_file': file_key,
                'output_file': output_filename
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }