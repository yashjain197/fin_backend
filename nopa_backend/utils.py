import boto3
from datetime import datetime, timedelta
from nopa_backend import settings


def upload_document(files):
    # Connect to AWS S3
    s3 = boto3.client('s3',
                      region_name=settings.AWS_S3_REGION,  # Use the appropriate region
                      aws_access_key_id=settings.AWS_S3_ACCESS_KEY,
                      aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY)

    uploaded_links = []
    for file in files:
        # Generate a unique key for each file (you can modify this as needed)
        s3_key = 'uploads/{}'.format(file.name)
        
        # Upload file to S3 bucket
        s3.upload_fileobj(file, settings.AWS_S3_BUCKET_NAME , s3_key)
        expiration = 604800 #about a week
        # Generate the URL for the uploaded file
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': settings.AWS_S3_BUCKET_NAME,
                                                'Key': s3_key},  ExpiresIn=expiration)  # URL expiration time in seconds
        
        uploaded_links.append(url)
        print(uploaded_links)
    return uploaded_links