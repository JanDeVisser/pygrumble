'''
Created on 2013-03-10

@author: jan
'''

import os
import smtplib
import mimetypes
import email
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.encoders import encode_base64
import jinja2

import gripe

logger = gripe.get_logger("gripe")

def sendMail(recipients, subject, text, *attachmentFilePaths, **headers):
    msg = MIMEMultipart()
    msg['From'] = gripe.Config.smtp.username
    msg['To'] = recipients if isinstance(recipients, basestring) else ",".join(recipients)
    msg['Subject'] = subject
    for header in headers:
        msg[header] = headers[header]
    msg.attach(MIMEText(text))
    for attachmentFilePath in attachmentFilePaths:
        msg.attach(getAttachment(attachmentFilePath))
    mailServer = smtplib.SMTP(gripe.Config.smtp.smtphost, gripe.Config.smtp.smtpport)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(gripe.Config.smtp.username, gripe.Config.smtp.password)
    mailServer.sendmail("%s <%s>" % (gripe.Config.smtp.fromname, gripe.Config.smtp.username), recipients, msg.as_string())
    mailServer.close()
    logger.info('Sent email to %s', recipients)

def getAttachment(attachmentFilePath):
    contentType, encoding = mimetypes.guess_type(attachmentFilePath)
    if contentType is None or encoding is not None:
        contentType = 'application/octet-stream'
    mainType, subType = contentType.split('/', 1)
    file = open(attachmentFilePath, 'rb')
    if mainType == 'text':
        attachment = MIMEText(file.read())
    elif mainType == 'message':
        attachment = email.message_from_file(file)
    elif mainType == 'image':
        attachment = MIMEImage(file.read(), _subType = subType)
    elif mainType == 'audio':
        attachment = MIMEAudio(file.read(), _subType = subType)
    else:
        attachment = MIMEBase(mainType, subType)
        attachment.set_payload(file.read())
    encode_base64(attachment)
    file.close()
    attachment.add_header('Content-Disposition', 'attachment', filename = os.path.basename(attachmentFilePath))
    return attachment

class TemplateMailMessage(object):
    template_dir = "mailtemplate"

    def __init__(self, template):
        self.template = template
        self._attachments = []
        self._headers = {}

    @classmethod
    def _get_env(cls):
        if not hasattr(cls, "env"):
            loader = jinja2.ChoiceLoader([ \
                jinja2.FileSystemLoader("%s/%s" % (gripe.root_dir(), cls.template_dir)), \
                jinja2.PackageLoader("gripe", "template") \
            ])
            env = jinja2.Environment(loader = loader)
            if hasattr(cls, "get_env") and callable(cls.get_env):
                env = cls.get_env(env)
            cls.env = env
        return cls.env

    def _get_context(self, ctx = None):
        if not ctx:
            ctx = {}
        ctx['app'] = gripe.Config.app.get("about", {})
        if hasattr(self, "get_context") and callable(self.get_context):
            ctx = self.get_context(ctx)
        return ctx

    def _get_template(self):
        ret = self.template \
            if hasattr(self, "template") \
            else None
        if not ret:
            ret = self.get_template() \
                if hasattr(self, "get_template") and callable(self.get_template) \
                else None
        cname = self.__class__.__name__.lower()
        if not ret:
            ret = cname
        ret = gripe.Config.app.get(cname, ret)
        logger.info("TemplateMailMessage: using template %s", ret)
        return ret
    
    def set_header(self, header, value):
        self._headers[header] = value
        
    def add_attachment(self, att_path):
        self._attachments.append(att_path)

    def render(self, ctx = None):
        ctx = self._get_context(ctx)
        return self._get_env().get_template(self._get_template() + ".txt").render(ctx)

    def send(self, recipients, subject, ctx = None):
        # FIXME Make subject template/config something
        recipients = recipients if not isinstance(recipients, basestring) else [ recipients ]
        recipient_str = ",".join(recipients)
        if ctx is None:
            ctx = {}
        ctx["subject"] = subject
        ctx["recipients"] = recipients
        ctx["recipient_str"] = recipient_str
        ctx['app'] = gripe.Config.app.get("about", {})
        body = self.render(ctx)
        return sendMail(recipients, subject, body, *self._attachments, **self._headers)

if __name__ == '__main__':
    sendMail("jan@de-visser.net", "Test", """
Hi Jan,
    
This is a test.

Thanks,

jan
""", *[ "%s/image/Desert.jpg" % gripe.root_dir() ])


    msg = TemplateMailMessage("testmessage")
    msg.send("jan@de-visser.net", "Test")
