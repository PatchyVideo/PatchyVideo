import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header

from datetime import datetime

def send_noreply(dst, title, body, mime = 'plain') :
	smtp = smtplib.SMTP()
	smtp.connect('172.17.0.1')

	msgRoot = MIMEMultipart("alternative")
	msgRoot['Subject'] = Header(title, "utf-8")
	msgRoot['From'] = "PatchyVideo<noreply@patchyvideo.com>"
	msgRoot['To'] = dst
	text = MIMEText(body, mime, "utf-8")
	msgRoot.attach(text)
	smtp.sendmail("noreply@patchyvideo.com", dst, msgRoot.as_string())

if __name__ == '__main__' :
	cur_time = str(datetime.now())
	send_noreply('zyddnys@outlook.com', 'Password reset', f'You have requested a password reset at {cur_time}, click the following link if you are the one requesting this reset.')
