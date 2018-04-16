import os
import sys
from flask import Flask
from flask import request
from flask import abort
from flask import send_file

from linebot import LineBotApi
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent
from linebot.models import TextMessage
from linebot.models import TextSendMessage
from linebot.models import ImageMessage
from linebot.models import ImageSendMessage

import numpy as np

import tempfile
import histeq

app = Flask(__name__)

# 環境変数からchannel_secret・channel_access_tokenを取得
channel_secret = os.environ['LINE_CHANNEL_SECRET']
channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/")
def hello_world():
    return "hello world!"


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    #return 'OK'
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    line_bot_api.reply_message(
        event.reply_token,
        #TextSendMessage(text=event.message.text))
        TextSendMessage(text=evt2reply(event)))


from botread import texts as word_dict
from botread import includes as include_dict
def evt2reply(event):

    if event.message.text == 'ls':
        return '    '.join(os.listdir())

    if event.message.text == 'ls2':
        return '    '.join(os.listdir('./tmp'))

    for line in include_dict:
        words = line.split(',')
        if len(words)==2:
            evt, reply = words
            if evt in event.message.text:
                return reply

    for line in word_dict:
        words = line.split(',')
        if len(words)==2:
            evt, reply = words
            if evt == event.message.text:
                return reply

    return 'hello world!'


#from skimage import io as skio
from PIL import Image

# image event
@handler.add(MessageEvent, message=ImageMessage)
def handle_content_message(event):

    '''
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text='これ画像ファイルだよね？'),
        TextSendMessage(text='これ画像ファイル....')])
    '''

    message_content = line_bot_api.get_message_content(event.message.id)
    # とりあえず保存
    ext = 'jpg'
    with tempfile.NamedTemporaryFile(dir='tmp', prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = '%s.%s' % (tempfile_path, ext)
    os.rename(tempfile_path, dist_path)

    img = Image.open(dist_path).convert('RGB')
    ma = max(img.size)

    if ma > 240:
        #sml_img.thumbnail((240,240), Image.ANTIALIAS)
        sml_img = resize(img, 240)
    else:
        sml_img = img.copy()

    if ma > 1024:
        #big_img.thumbnail((1024,1024), Image.ANTIALIAS)
        big_img = resize(img, 1024)
    else:
        big_img = img.copy()

    sml_img = Image.fromarray(histeq.histeq_main(np.array(sml_img)))
    big_img = Image.fromarray(histeq.histeq_main(np.array(big_img)))

    sml_img.save('tmp/sml.jpg')
    big_img.save('tmp/big.jpg')


    baseurl = 'https://afternoon-escarpment-17016.herokuapp.com'

    messages = ImageSendMessage(
        original_content_url='%s/tmp/big.jpg' % baseurl,
        preview_image_url="%s/tmp/sml.jpg" % baseurl)

    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text='これ画像ファイルだよね？'),
         TextSendMessage(text='明るくしてみます！'),
         messages])

    os.remove(dist_path)
    os.remove('tmp/sml.png')
    os.remove('tmp/big.png')


def resize(img, s):
    w,h = img.size
    if w>h:
        ww = s
        hh = s*h//w
    else:
        hh = s
        ww = s*w//h
    return img.resize((ww, hh), Image.BILINEAR)



# URLをたたいて画像を読み出せるようにしておく
@app.route("/tmp/<name>")
def img_show(name):
    return send_file('tmp/%s' % name)


if __name__ == "__main__":
    app.run()
