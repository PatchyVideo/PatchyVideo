import smtplib

from datetime import datetime

def send_noreply(dst, title, text) :
	SERVER = "172.17.0.1"

	FROM = "noreply@patchyvideo.com"
	TO = [dst] # must be a list

	SUBJECT = title

	TEXT = text

	# Prepare actual message

	message = """\
	From: %s
	To: %s
	Subject: %s

	%s
	""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

	# Send the mail

	server = smtplib.SMTP(SERVER)
	server.sendmail(FROM, TO, message.encode('utf-8'))
	server.quit()

if __name__ == '__main__' :
	cur_time = str(datetime.now())
	send_noreply('zyddnys@outlook.com', 'Reset your password', f'You have requested a password reset at {cur_time}, click the following link if you are the one requesting this reset.')
