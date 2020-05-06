########################################################################################################################
# ------------------------------------------ server params -------------------------------------------------------------
########################################################################################################################
from io import BytesIO

from PIL import Image

CLIENT_LIST = ('127.0.0.1', '192.168.1.70')
MAX_IMG_SIZE = (64, 64)


########################################################################################################################
# ----------------------------------------------- proxy logic ----------------------------------------------------------
########################################################################################################################
def proxy_common_move(req_handler, get_method):
    def image_to_byte_array(image):
        imgByteArr = BytesIO()
        image.save(imgByteArr, format=image.format)
        imgByteArr = imgByteArr.getvalue()
        return imgByteArr

    if req_handler.client_address[0] in CLIENT_LIST:
        req_res = req_handler.path
        print('requested resource %s' % req_res)
        resp = get_method(req_res)

        changed_content = resp.content
        changed_content_length = None

        req_handler.send_response(resp.status_code)
        for keyword, value in dict(resp.headers).items():
            # print("%s:%s" % (keyword, value))
            if keyword.lower() == 'content-type':

                print('content-type:%s' % value)
                req_handler.send_header(keyword, value)

                if value.lower() == 'image/png':
                    img = Image.open(BytesIO(resp.content))
                    if img.size[0] > MAX_IMG_SIZE[0] or img.size[1] > MAX_IMG_SIZE[1]:
                        try:
                            img.thumbnail(MAX_IMG_SIZE)
                            print("img compressed")
                        except ZeroDivisionError:
                            pass
                        changed_content = image_to_byte_array(img)
                        changed_content_length = len(image_to_byte_array(img))
            elif keyword.lower() in ('content-length',):
                if changed_content_length is not None:
                    req_handler.send_header(keyword, str(changed_content_length))
                else:
                    req_handler.send_header(keyword, value)
        req_handler.end_headers()
        return changed_content

    else:
        return None
