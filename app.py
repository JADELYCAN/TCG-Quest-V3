from flask import Flask, request, jsonify, send_from_directory
import cv2, numpy as np
app=Flask(__name__)

def measure(file):
    data=np.frombuffer(file.read(),np.uint8); img=cv2.imdecode(data,cv2.IMREAD_COLOR)
    if img is None: raise ValueError('Invalid image')
    h,w=img.shape[:2]; scale=min(1,1400/max(h,w)); img=cv2.resize(img,None,fx=scale,fy=scale) if scale<1 else img
    h,w=img.shape[:2]; gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    # Estimate the photographed background from the four image corners.
    # Compare LAB colors to the background instead of using a fixed gray cutoff:
    # this handles white, cream, and softly shaded photo backgrounds.
    lab_img=cv2.cvtColor(img,cv2.COLOR_BGR2LAB).astype(np.float32)
    pad=max(8,int(min(h,w)*.045))
    patches=[lab_img[:pad,:pad],lab_img[:pad,-pad:],lab_img[-pad:,:pad],lab_img[-pad:,-pad:]]
    bg=np.median(np.concatenate([q.reshape(-1,3) for q in patches]),axis=0)
    distance=np.linalg.norm(lab_img-bg,axis=2)
    blurred=cv2.GaussianBlur(distance,(7,7),0)
    masks=[]
    for threshold in (13,19,26,34):
        mask=np.uint8(blurred>threshold)*255
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((17,17),np.uint8))
        mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
        masks.append(mask)
    candidates=[]
    for mask in masks:
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area=cv2.contourArea(contour)
            if not (.20*w*h<area<.92*w*h):continue
            rect=cv2.minAreaRect(contour)
            rw,rh=rect[1]
            if min(rw,rh)<1:continue
            aspect=max(rw,rh)/min(rw,rh)
            if not 1.22<aspect<1.72:continue
            box=cv2.boxPoints(rect).astype(np.float32)
            if np.any(box[:,0]<-5) or np.any(box[:,1]<-5) or np.any(box[:,0]>w+5) or np.any(box[:,1]>h+5):continue
            fill=area/max(rw*rh,1)
            if fill<.76:continue
            # Favor filled card-like silhouettes over fragmented artwork.
            score=area*(.5+.5*min(fill,1))
            candidates.append((score,box,contour,mask))
    if not candidates:
        raise ValueError('Card outline not detected confidently. Use a plain contrasting background and show all four edges.')
    _,pts,physical_contour,physical_mask=max(candidates,key=lambda c:c[0])
    s=pts.sum(axis=1); d=np.diff(pts,axis=1).flatten()
    corners=np.array([pts[np.argmin(s)],pts[np.argmin(d)],pts[np.argmax(s)],pts[np.argmax(d)]],dtype=np.float32)
    dst=np.array([[0,0],[599,0],[599,839],[0,839]],dtype=np.float32)
    transform=cv2.getPerspectiveTransform(corners,dst)
    warp=cv2.warpPerspective(img,transform,(600,840))
    # Warp the same silhouette used for outer-edge detection.
    physical_contour=cv2.approxPolyDP(physical_contour,0.002*cv2.arcLength(physical_contour,True),True)
    warped_contour=cv2.perspectiveTransform(physical_contour.astype(np.float32),transform)
    # Derive initial editable corner positions from the silhouette in the
    # rectified photo; these are estimates, never locked controls.
    contour_pts=warped_contour.reshape(-1,2)
    contour_pts[:,0]=np.clip(contour_pts[:,0],0,599)
    contour_pts[:,1]=np.clip(contour_pts[:,1],0,839)
    # Estimate edge locations away from the rounded corners.
    middle_x=contour_pts[(contour_pts[:,1]>250)&(contour_pts[:,1]<590),0]
    middle_y=contour_pts[(contour_pts[:,0]>180)&(contour_pts[:,0]<420),1]
    if len(middle_x)>3 and len(middle_y)>3:
        x0,x1=float(np.min(middle_x)),float(np.max(middle_x))
        y0,y1=float(np.min(middle_y)),float(np.max(middle_y))
    else:
        x0,x1,y0,y1=3.,596.,3.,836.
    auto_corners=[[round(x0,1),round(y0,1)],[round(x1,1),round(y0,1)],
                  [round(x1,1),round(y1,1)],[round(x0,1),round(y1,1)]]
    # Detect PRINTED frame boundaries independently from the physical card edge.
    # Sample many scan lines; a true straight frame should recur in most strips.
    g=cv2.cvtColor(warp,cv2.COLOR_BGR2GRAY)
    lab=cv2.cvtColor(warp,cv2.COLOR_BGR2LAB).astype(np.float32)

    def frame_boundary(axis, side):
        length=600 if axis=='x' else 840
        other=840 if axis=='x' else 600
        low=int(length*.025)
        high=int(length*.19)
        samples=[]
        # Exclude corners, where frame graphics are often curved or interrupted.
        for fraction in np.linspace(.24,.76,13):
            center=int(other*fraction)
            if axis=='x':
                strip=lab[max(0,center-5):min(840,center+6),:,:]
                profile=np.median(strip,axis=0)
            else:
                strip=lab[:,max(0,center-5):min(600,center+6),:]
                profile=np.median(strip,axis=1)
            if side=='end': profile=profile[::-1]
            profile=cv2.GaussianBlur(profile.reshape(1,-1,3),(9,1),0).reshape(-1,3)
            gradient=np.linalg.norm(np.diff(profile,axis=0),axis=1)
            search=gradient[low:high]
            if search.size<3: continue
            # Keep multiple candidate edges rather than forcing one per strip.
            local=[]
            for i in range(1,len(search)-1):
                if search[i]>=search[i-1] and search[i]>=search[i+1] and search[i]>=5.0:
                    local.append((low+i,float(search[i])))
            samples.append(sorted(local,key=lambda x:x[1],reverse=True)[:5])
        # Candidate must appear across many different strips at the same position.
        options=[]
        for pos in range(low,high):
            matches=[]
            for sample in samples:
                nearby=[(p,strength) for p,strength in sample if abs(p-pos)<=5]
                if nearby: matches.append(max(nearby,key=lambda x:x[1]))
            support=len(matches)
            if support:
                score=support*min(30.0,float(np.median([x[1] for x in matches])))
                options.append((score,support,pos,matches))
        if not options: return None,0
        score,support,pos,matches=max(options,key=lambda x:x[0])
        if support<10: return None,support/len(samples) if samples else 0
        detected=int(round(np.median([p for p,_ in matches])))
        return (length-1-detected if side=='end' else detected),support/len(samples)

    l,cl=frame_boundary('x','start')
    r,cr=frame_boundary('x','end')
    t,ct=frame_boundary('y','start')
    b,cb=frame_boundary('y','end')
    valid=(all(v is not None for v in (l,r,t,b)) and
           r-l>350 and b-t>550 and
           min(l,599-r,t,839-b)>=5)
    confidence='moderate' if valid else 'low'
    horizontal=vertical=None
    borders={'left':None,'right':None,'top':None,'bottom':None}
    if valid:
        left,right,top,bottom=float(l),float(599-r),float(t),float(839-b)
        # Reject extreme ratios: these are usually artwork edges, not printed frames.
        # Such cards require manual border confirmation rather than a false percentage.
        if min(left,right)/max(left,right)<.54 or min(top,bottom)/max(top,bottom)<.54:
            valid=False
            confidence='low'
    if valid:
        left,right,top,bottom=float(l),float(599-r),float(t),float(839-b)
        def ratio(a,b): return [round(100*a/(a+b),1),round(100*b/(a+b),1)]
        horizontal=ratio(left,right)
        vertical=ratio(top,bottom)
        borders={'left':round(left,1),'right':round(right,1),'top':round(top,1),'bottom':round(bottom,1)}
        for x in (l,r): cv2.line(warp,(int(x),0),(int(x),839),(0,230,255),2)
        for y in (t,b): cv2.line(warp,(0,int(y)),(599,int(y)),(0,230,255),2)
    # Provide an unannotated image for interactive green/yellow editing.
    clean_warp=cv2.warpPerspective(img,transform,(600,840))
    _,clean_buffer=cv2.imencode('.jpg',clean_warp,[cv2.IMWRITE_JPEG_QUALITY,90])
    clean_image='data:image/jpeg;base64,'+__import__('base64').b64encode(clean_buffer).decode()
    # Green shows the rectified PHYSICAL card boundary; yellow shows the
    # estimated printed border only if detection passed the consistency test.
    if warped_contour is not None:
        # Show the actual detected rounded silhouette, not an artificial rectangle.
        cv2.drawContours(warp,[np.rint(warped_contour).astype(np.int32)],-1,(70,240,100),2)
    else:
        cv2.rectangle(warp,(0,0),(599,839),(70,240,100),2)
    import base64
    _,buff=cv2.imencode('.jpg',warp,[cv2.IMWRITE_JPEG_QUALITY,85])
    annotated='data:image/jpeg;base64,'+base64.b64encode(buff).decode()
    warning=('Experimental estimate only: verify that yellow lines follow the printed frame. '
             'This is not a PSA grade prediction.' if valid else
             'Printed border could not be located consistently. No centering percentages '
             'were calculated. Try a sharper, straight-on photo with even lighting.')
    # Image quality indicators are NOT card condition or defect detection.
    # Restrict metrics to the rectified card crop to avoid background bias.
    quality_gray=cv2.cvtColor(clean_warp,cv2.COLOR_BGR2GRAY)
    sharpness=float(cv2.Laplacian(quality_gray,cv2.CV_64F).var())
    hsv=cv2.cvtColor(clean_warp,cv2.COLOR_BGR2HSV)
    glare_fraction=float(np.mean((hsv[:,:,2]>246)&(hsv[:,:,1]<42)))
    quality={'sharpness_score':round(sharpness,1),
             'possible_glare_percent':round(glare_fraction*100,1),
             'sharpness_flag':'review' if sharpness<65 else 'ok',
             'glare_flag':'review' if glare_fraction>.07 else 'ok'}
    return {'horizontal':horizontal,'vertical':vertical,'border_pixels':borders,
            'confidence':confidence,'photo_quality':quality,'annotated':annotated,'clean_image':clean_image,'auto_corners':auto_corners,'warning':warning}

@app.get('/')
def home(): return send_from_directory('.','index.html')
@app.post('/api/measure')
def api():
    try:
        if 'front' not in request.files: return jsonify(error='Upload a front image'),400
        front=measure(request.files['front']); back=measure(request.files['back']) if request.files.get('back') else None
        return jsonify(front=front,back=back,grade=None,grade_status='Not determined: corner, edge, surface, print quality and eye appeal require validated inspection. No official PSA grade is generated.')
    except ValueError as e:return jsonify(error=str(e)),422
    except Exception:return jsonify(error='Image analysis failed'),500
@app.get('/api/market/status')
def market_status():
    import os
    return jsonify(ebay_configured=bool(os.getenv('EBAY_CLIENT_ID') and os.getenv('EBAY_CLIENT_SECRET')),tcgplayer_configured=bool(os.getenv('TCGPLAYER_ACCESS_TOKEN')),note='Listings are not completed sales; asking prices are not verified market values.')

@app.get('/api/market/search')
def market_search():
    import os, json, urllib.request, urllib.parse, base64
    q=(request.args.get('q') or '').strip()[:120]
    source=(request.args.get('source') or 'ebay').lower()
    if len(q)<2: return jsonify(error='Enter at least two characters'),400
    if source=='ebay':
        client=os.getenv('EBAY_CLIENT_ID'); secret=os.getenv('EBAY_CLIENT_SECRET')
        if not (client and secret): return jsonify(error='eBay API not configured. Add EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to Render environment variables.'),503
        try:
            auth=base64.b64encode((client+':'+secret).encode()).decode()
            body=urllib.parse.urlencode({'grant_type':'client_credentials','scope':'https://api.ebay.com/oauth/api_scope'}).encode()
            req=urllib.request.Request('https://api.ebay.com/identity/v1/oauth2/token',data=body,headers={'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'},method='POST')
            with urllib.request.urlopen(req,timeout=12) as r: token=json.load(r)['access_token']
            url='https://api.ebay.com/buy/browse/v1/item_summary/search?'+urllib.parse.urlencode({'q':q,'limit':16})
            req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'X-EBAY-C-MARKETPLACE-ID':'EBAY_US'})
            with urllib.request.urlopen(req,timeout=12) as r: data=json.load(r)
            items=[]
            for x in data.get('itemSummaries',[]):
                price=x.get('price') or {}
                items.append({'title':x.get('title','Untitled'),'price':price.get('value'),'currency':price.get('currency'),'image':(x.get('image') or {}).get('imageUrl'),'url':x.get('itemWebUrl'),'source':'eBay active listing'})
            return jsonify(items=items,disclaimer='Active listing asking prices only. Not completed sales or verified card valuations.')
        except Exception as e:
            app.logger.warning('eBay API error: %s',str(e))
            return jsonify(error='eBay API request failed. Check credentials, Browse API eligibility, and Render logs.'),502
    if source=='tcgplayer':
        return jsonify(error='TCGplayer catalog/pricing requires approved API access and an integration adapted to the granted endpoints. No TCGplayer data is connected yet.'),503
    return jsonify(error='Unknown source'),400


# Photo identification uses a configured vision API; no guesses are made without it.
@app.get('/api/identify/status')
def identify_status():
    import os
    return jsonify(available=bool(os.getenv('OPENAI_API_KEY')),note='Photo identification requires OPENAI_API_KEY on Render; API usage may incur charges.')

@app.post('/api/identify')
def identify_card():
    import os, json, base64, urllib.request, urllib.error
    key=os.getenv('OPENAI_API_KEY')
    if not key:
        return jsonify(error='Photo identification is not configured. Add OPENAI_API_KEY in Render Environment, then redeploy.'),503
    uploaded=request.files.get('front')
    if not uploaded: return jsonify(error='Upload a front photo first.'),400
    raw=uploaded.read(6*1024*1024+1)
    if len(raw)>6*1024*1024: return jsonify(error='Photo must be 6 MB or smaller.'),413
    arr=np.frombuffer(raw,np.uint8)
    img=cv2.imdecode(arr,cv2.IMREAD_COLOR)
    if img is None: return jsonify(error='Please upload a valid image.'),422
    h,w=img.shape[:2]
    if max(h,w)>1200:
        scale=1200/max(h,w)
        img=cv2.resize(img,(max(1,int(w*scale)),max(1,int(h*scale))))
    ok,encoded=cv2.imencode('.jpg',img,[cv2.IMWRITE_JPEG_QUALITY,82])
    if not ok: return jsonify(error='Could not prepare image.'),422
    data_url='data:image/jpeg;base64,'+base64.b64encode(encoded.tobytes()).decode('ascii')
    instructions=('Identify this trading card from the front photo. Supported categories: Pokémon, One Piece, sports, or unknown. '
        'Read only visible text and symbols. Never invent a player, set, card number, year, rarity or variant. '
        'Return ONLY a JSON object with keys category, name, set, number, year, variant, confidence, evidence, caveat. '
        'category must be one of Pokemon, One Piece, Sports, Unknown. '
        'confidence must be high, medium, or low; use low for uncertain or unreadable images. '
        'All other fields must be strings, empty string when unreadable. '
        'evidence should briefly cite visible text, not external facts. '
        'caveat should mention when exact set/variant needs checking against a catalog. '
        'This is an image-based tentative identification, not catalog verification or authenticity grading.')
    payload={'model':os.getenv('OPENAI_VISION_MODEL','gpt-4o-mini'), 'temperature':0,
        'response_format':{'type':'json_object'}, 'max_tokens':350,
        'messages':[{'role':'system','content':instructions},
                    {'role':'user','content':[{'type':'text','text':'Identify the card. If uncertain, say so.'},
                                               {'type':'image_url','image_url':{'url':data_url,'detail':'high'}}]}]}
    req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),
         headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=35) as response: result=json.load(response)
        raw_result=result['choices'][0]['message']['content']
        obj=json.loads(raw_result)
        if not isinstance(obj,dict): raise ValueError('Invalid response')
        category=obj.get('category','Unknown')
        if category not in ('Pokemon','One Piece','Sports','Unknown'):category='Unknown'
        confidence=obj.get('confidence','low')
        if confidence not in ('high','medium','low'):confidence='low'
        clean={k:str(obj.get(k,'') or '')[:160] for k in ('name','set','number','year','variant','evidence','caveat')}
        return jsonify(category=category,confidence=confidence,**clean,
          verified=False,disclaimer='Tentative AI identification. Verify the card number, set and variant before adding it to a collection. Not an authenticity or grade assessment.')
    except urllib.error.HTTPError as e:
        app.logger.warning('Identification API HTTP error %s',e.code)
        return jsonify(error='Identification provider rejected the request. Check the API key, billing, and model access in Render.'),502
    except Exception as e:
        app.logger.warning('Identification failed: %s',str(e))
        return jsonify(error='Could not identify this photo right now. Try a clear, straight-on photo with readable text.'),502

if __name__=='__main__': app.run(host='0.0.0.0',port=int(__import__('os').environ.get('PORT',5050)),debug=False)
