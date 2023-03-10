"""
Utility scripts for sending emails and other tasks
"""

# External modules
import os
import sys
import cv2
import numpy as np
import pandas as pd
import email.message
import googleapiclient.discovery
from base64 import urlsafe_b64encode
from email.message import EmailMessage
from google_auth_oauthlib.flow import InstalledAppFlow


def get_gmail_service(scopes:str or list, credentials:str, port:int=0) -> googleapiclient.discovery:
    """
    Using the googleapiclient.discovery.build method to get a service connection to the gmail API

    Parameters
    ----------
    credentials : str
        Path to the credentials.json file
    port : int, optional
        Port to use for the local server, by default 0

    Returns
    -------
    googleapiclient.discovery
        Service connection to the gmail API
    """
    # Input checks
    scopes = str2list(scopes)
    assert isinstance(scopes, list), f"Scopes should be a list, not {type(scopes)}"
    assert os.path.exists(credentials), f"Credentials file {credentials} does not exist"
    # Use the local and secret 
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file=credentials, scopes=scopes)
    creds = flow.run_local_server(port=port)
    service = googleapiclient.discovery.build('gmail', 'v1', credentials=creds)
    return service


def create_message(message:str, email_from:str, email_to:str, subject:str, folder_attachents:str, attachment_suffix:str or list, max_image_size:int=1024) -> email.message:
    """
    Use the email.message.EmailMessage class to create a message and return its raw base64 encoded version in a dictionary

    Parameters
    ----------
    message : str
        Message to send
    email_from : str
        Email address to send from
    email_to : str
        Email address to send to
    subject : str
        Subject line
    folder_attachents : str
        Path to the folder containing the attachments
    attachment_suffix : str or list
        Suffix of the attachment to send
    
    Returns
    -------
    dict
        Dictionary with the raw base64 encoded message
    """
    # Input checks
    assert isinstance(message, str), f"Message should be a string, not {type(message)}"
    assert isinstance(email_from, str), f"Email_from should be a string, not {type(email_from)}"
    assert isinstance(email_to, str), f"Email_to should be a string, not {type(email_to)}"
    assert isinstance(subject, str), f"Subject should be a string, not {type(subject)}"
    assert os.path.exists(folder_attachents), f"Folder {folder_attachents} does not exist"
    attachment_suffix = str2list(attachment_suffix)
    assert isinstance(attachment_suffix, list), f"Attachment_suffix should be a list, not {type(attachment_suffix)}"
    # Create the message
    msg = EmailMessage()
    msg.set_content(message)
    msg['To'] = email_to
    msg['From'] = email_from
    msg['Subject'] = subject
    # Find the attachments
    files = find_files_with_suffix(folder_attachents, attachment_suffix)
    print(f"Found {len(files)} files with suffix {attachment_suffix} in folder {folder_attachents}: {files}")
    # Add the attachments
    for file in files:
        subtype = file.split('.')[-1]
        path = os.path.join(folder_attachents, file)
        is_image = is_file_image(path)
        if is_image:
            data = image2bytes(path=path, max_size=max_image_size)
        else:
            with open(path, 'rb') as fp:
                data = fp.read()
        msg.add_attachment(data, maintype='image', subtype=subtype)
    # Return the message
    return msg


def message2bytes(msg) -> dict:
    # Encode the message and save it in a dictionary
    encoded_msg = urlsafe_b64encode(msg.as_bytes()).decode()
    di_msg = {'raw': encoded_msg}
    return di_msg


def find_files_with_suffix(folder:str, suffix:str or list) -> list:
    """
    Search a folder for all files with a certain suffix

    Parameters
    ----------
    folder : str
        Path to the folder to search
    suffix : str or list, optional
        Suffix of the files to search for, by default 'txt'

    Returns
    -------
    pd.Series
        Series of all files with the correct suffix in the folder
    
    Example
    -------
    >>> find_files_with_suffix('data','txt')
    0    file1.txt
    1    file2.txt
    dtype: object
    """
    # Input checks
    assert os.path.exists(folder), f"Folder {folder} does not exist"
    suffix = str2list(suffix)
    # Find all files in the folder
    files = pd.Series(os.listdir(folder))
    file_suffixes = files.str.split('.',regex=False).apply(lambda x: x[-1],1).to_list()
    # Find all files with the correct suffix
    idx_suffix = [file_suffix in suffix for file_suffix in file_suffixes]
    files_suffix = files[idx_suffix].to_list()
    return files_suffix


def str2list(string:str or list):
    """
    Check if a string is a list, if not, make it a list

    Parameters
    ----------
    string : str or list
        String to check

    Returns
    -------
    list
        List of the string
    """
    if isinstance(string, str):
        return [string]
    else:
        return string


def process_email_list(folder:str, file_suffix:str='txt') -> list:
    """
    This function searched through a folder, find all the files that end with a certain suffix (default .txt), and then parses the files and returns a list of all the emails in the files. The function should return a list of emails, where each email is a string. The function should also print out the number of emails found in the folder.

    Parameters
    ----------
    folder : str
        Path to the folder to search
    file_suffix : str, optional
        Suffix of the files to search for, by default 'txt'
    
    Returns
    -------
    list
        List of all emails found in the folder
    """
    # Input checks
    assert os.path.exists(folder), f"Folder {folder} does not exist"
    # Find all files in the folder
    files = find_files_with_suffix(folder, file_suffix)
    # Find all emails in the files
    emails = []
    for file in files:
        with open(os.path.join(folder,file)) as f:
            emails.extend(f.read().splitlines())
    # Make sure all emails are lists
    emails = [str2list(email) for email in emails]
    # Combine all emails to a single string
    emails = pd.Series(' '.join([' '.join(email) for email in emails]))
    # set to lower case
    emails = emails.str.lower()
    # Split on any possible spaces
    emails = pd.Series(' '.join(emails[0].split()))
    # Seperate on any possible delimiters
    emails = emails.str.split('\\s|\\;|\\n').explode().reset_index(drop=True)
    # Valid email must have an amperstand
    emails = emails[emails.str.contains('\\@',regex=True)]
    # Remove the <> from the emails
    emails = emails.str.replace('\\<|\\>','',regex=True)
    # Return list
    emails = emails.to_list()
    print(f"Found {len(emails)} emails in {folder}")
    return emails


def press_Yn_to_continue():
    """
    Force the user to press Y to continue, n to break, or repeat options
    """
    inp = input('Press Y to continue, or n to break\n')
    print('You pressed', inp)
    while (inp != 'Y') and (inp != 'n'):        # Loop until it is a blank line
        print('You did not press Y or n, try again')
        inp = input()
        print('You pressed', inp)
    if inp == 'n':
        sys.exit('You pressed n, breaking')


def is_file_image(path:str) -> bool:
    """Check whether a file is an image"""
    # Input checks
    assert os.path.exists(path), f"{path} does not exist"
    check = path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))
    return check


def image2bytes(path:str, max_size:int=1024) -> bytes:
    """
    Convert an image to bytes

    Parameters
    ----------
    path : str
        Path to the image
    max_size : int, optional
        Maximum size of the image, by default 1024
    
    Returns
    -------
    bytes
        Bytes of the image
    """
    # Check the image exists
    assert os.path.exists(path), f"{path} does not exist"
    # Check the image is an image
    assert is_file_image(path), f"{path} is not an image"
    # Read the image
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    # Resize the image if it exceeds the maximum size
    dim_max = np.argmax(img.shape[:2])
    pixels_max = img.shape[dim_max]
    if pixels_max > max_size:
        scale = max_size / pixels_max
        img = cv2.resize(img, None, fx=scale, fy=scale)
    # Convert to bytes
    suffix = path.split('.')[-1]
    raw = cv2.imencode(f'.{suffix}', img)[1].tobytes()
    assert isinstance(raw, bytes), f"Data should be bytes, not {type(raw)}"
    return raw
