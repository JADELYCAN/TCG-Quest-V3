"""AI avatar banner editor. Server-side only: never expose OPENAI_API_KEY to browsers."""
import base64
import io
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from flask import Blueprint, jsonify, request

avatar_bp = Blueprint('collector_avatar', __name__)
BASE = Path(__file__).resolve().parent
MAX_UPLOAD = 6 * 1024 * 1024

@avatar_bp.get('/api/avatar/status')
def avatar_status():
    return jsonify(available=bool(os.getenv('OPENAI_API_KEY')), model=os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-1.5'))


def image_upload(upload):
    if not upload or not upload.mimetype.startswith('image/'):
        raise ValueError('Upload a JPEG, PNG or WebP selfie.')
    data = upload.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise ValueError('Photo must be smaller than 6 MB.')
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert('RGB')
        if img.width < 150 or img.height < 150:
            raise ValueError('Use a clearer photo at least 150 pixels wide and tall.')
        img.thumbnail((1024, 1024))
        out = io.BytesIO(); img.save(out, format='PNG'); return out.getvalue()
    except ValueError:
        raise
    except Exception:
        raise ValueError('This image could not be opened. Try a JPEG or PNG.')


def multipart(fields, images):
    boundary = 'tcgquest' + uuid.uuid4().hex
    body = io.BytesIO()
    for key, val in fields.items():
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode())
    for field, filename, content in images:
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode())
        body.write(content); body.write(b'\r\n')
    body.write(f'--{boundary}--\r\n'.encode())
    return body.getvalue(), f'multipart/form-data; boundary={boundary}'


@avatar_bp.post('/api/avatar/generate')
def avatar_generate():
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return jsonify(error='AI avatar generation is not configured. Add OPENAI_API_KEY to Render environment variables.'), 503
    try:
        selfie = image_upload(request.files.get('selfie'))
        hat = request.form.get('hat', 'Baseball cap')
        hat_color = request.form.get('hat_color', 'Green')
        clothing = request.form.get('clothing', 'Hoodie')
        clothing_color = request.form.get('clothing_color', 'Green')
        if hat not in ('Baseball cap', 'Beanie', 'No hat') or clothing not in ('Hoodie', 'Jersey', 'T-shirt') or hat_color not in ('Green','Blue','Red','Black','Orange') or clothing_color not in ('Green','Blue','Red','Black','Orange'):
            return jsonify(error='Invalid outfit choice.'), 400
        # Build a full-size, masked canvas. Editing ONLY the character's upper body
        # minimizes disturbance to the rest of the banner. Final composition below
        # guarantees original pixels outside the character region remain unchanged.
        original = Image.open(BASE / 'reference-banner.png').convert('RGB')
        w,h = original.size
        if (w,h) != (1536,234):
            return jsonify(error='Unexpected banner dimensions; expected 1536 x 234.'),500
        yoff=395
        canvas = Image.new('RGB',(1536,1024),(5,13,24))
        canvas.paste(original,(0,yoff))
        mask = Image.new('RGBA',canvas.size,(255,255,255,255))
        draw=ImageDraw.Draw(mask)
        # Transparent region = permitted edit. Keep large logo and neighboring characters intact.
        # Upper character (head, cap, shoulders) near x 700–870.
        polygon=[(705,397),(795,397),(830,411),(862,453),(877,509),(869,542),(843,546),(820,535),(790,533),(760,540),(723,541),(681,538),(664,516),(670,473),(686,430)]
        draw.polygon(polygon,fill=(0,0,0,0))
        b=io.BytesIO();canvas.save(b,format='PNG');banner_bytes=b.getvalue()
        m=io.BytesIO();mask.save(m,format='PNG');mask_bytes=m.getvalue()
        outfit=f'{hat_color.lower()} {hat.lower()}' if hat!='No hat' else 'no hat'
        prompt=(
          'Edit IMAGE 1 (the wide illustrated TCG Quest banner) using IMAGE 2 (the real selfie) as the identity reference. '
          'Only replace the CENTER cartoon collector wearing a green cap and green hoodie, with a recognizable cartoon likeness of the selfie person. '
          f'Dress the new illustrated collector in {outfit} and a {clothing_color.lower()} {clothing.lower()}. '
          'Match the original vibrant polished anime/comic illustration style, lighting, scale, shoulders, position and hand/card pose. '
          'The character must fit the existing central space and remain BEHIND the TCG QUEST logo. '
          'DO NOT change any text, logos, cards, Pikachu, Luffy, football player, basketball player, background, layout, or other characters. '
          'Do not draw an additional portrait, inset, frame, circle or photograph. Replace the existing illustrated character naturally. '
          'Keep all pixels outside the masked edit area unchanged.'
        )
        payload, content_type=multipart(
            {'model':os.getenv('OPENAI_IMAGE_MODEL','gpt-image-1.5'),'prompt':prompt,'size':'1536x1024','quality':'medium','output_format':'png'},
            [('image[]','banner.png',banner_bytes),('image[]','selfie.png',selfie),('mask','mask.png',mask_bytes)])
        req=urllib.request.Request('https://api.openai.com/v1/images/edits',data=payload,
             headers={'Authorization':'Bearer '+key,'Content-Type':content_type},method='POST')
        with urllib.request.urlopen(req,timeout=175) as res:
            result=json.load(res)
        encoded=result['data'][0]['b64_json']
        edited=Image.open(io.BytesIO(base64.b64decode(encoded))).convert('RGB')
        if edited.size!=(1536,1024):
            edited=edited.resize((1536,1024),Image.Resampling.LANCZOS)
        patch=edited.crop((0,yoff,w,yoff+h))
        # Only blend the character's region. Original outside remains pixel-identical.
        blend=Image.new('L',(w,h),0); d=ImageDraw.Draw(blend)
        d.polygon([(x,y-yoff) for x,y in polygon],fill=255)
        blend=blend.filter(ImageFilter.GaussianBlur(3))
        final=Image.composite(patch,original,blend)
        out=io.BytesIO();final.save(out,format='JPEG',quality=88,optimize=True)
        return jsonify(image='data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode(),note='AI-created cartoon banner. The original banner is retained outside the central character area.')
    except ValueError as exc:
        return jsonify(error=str(exc)),400
    except urllib.error.HTTPError as exc:
        avatar_bp.logger.warning('Image API HTTP %s',exc.code) if hasattr(avatar_bp,'logger') else None
        return jsonify(error=f'Image generation failed (provider HTTP {exc.code}). Check API billing, model access, or try again.'),502
    except Exception:
        return jsonify(error='Image generation failed or timed out. Please retry with a clear selfie.'),502
