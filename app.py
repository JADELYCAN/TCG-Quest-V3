from flask import Flask, request, jsonify, send_from_directory
import cv2, numpy as np
app=Flask(__name__)

def measure(file):
    data=np.frombuffer(file.read(),np.uint8); img=cv2.imdecode(data,cv2.IMREAD_COLOR)
    if img is None: raise ValueError('Invalid image')
    h,w=img.shape[:2]; scale=min(1,1400/max(h,w)); img=cv2.resize(img,None,fx=scale,fy=scale) if scale<1 else img
    h,w=img.shape[:2]; gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    blur=cv2.GaussianBlur(gray,(5,5),0); edges=cv2.Canny(blur,45,140)
    cnts,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    quads=[]
    for c in cnts:
        p=cv2.arcLength(c,True); a=cv2.approxPolyDP(c,.025*p,True)
        if len(a)==4 and cv2.isContourConvex(a):
            area=cv2.contourArea(a)
            if .16*w*h<area<.98*w*h: quads.append((area,a.reshape(4,2).astype('float32')))
    # Rounded card corners often produce 8+ contour vertices, not four.
    # Prefer foreground segmentation on a pale background and use a rotated
    # rectangle to estimate the four *virtual* card corners.
    candidates=[]
    for threshold in (165, 180, 195):
        mask=np.uint8(gray < threshold)*255
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((11,11),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area=cv2.contourArea(contour)
            if not (.25*w*h < area < .92*w*h): continue
            rect=cv2.minAreaRect(contour)
            rw,rh=rect[1]
            if min(rw,rh)<1: continue
            aspect=max(rw,rh)/min(rw,rh)
            if not (1.18 < aspect < 1.8): continue
            box=cv2.boxPoints(rect).astype(np.float32)
            if np.min(box[:,0]) < -3 or np.min(box[:,1]) < -3 or np.max(box[:,0]) > w+3 or np.max(box[:,1]) > h+3: continue
            candidates.append((area,box))
    if candidates:
        pts=max(candidates,key=lambda x:x[0])[1]
    elif quads:
        pts=max(quads,key=lambda x:x[0])[1]
    else:
        raise ValueError('Card outline not detected. Use a plain contrasting background with all edges visible.')
    s=pts.sum(axis=1); d=np.diff(pts,axis=1).flatten()
    corners=np.array([pts[np.argmin(s)],pts[np.argmin(d)],pts[np.argmax(s)],pts[np.argmax(d)]],dtype=np.float32)
    dst=np.array([[0,0],[599,0],[599,839],[0,839]],dtype=np.float32)
    warp=cv2.warpPerspective(img,cv2.getPerspectiveTransform(corners,dst),(600,840))
    g=cv2.cvtColor(warp,cv2.COLOR_BGR2GRAY)
    # Look for the strongest near-continuous interior printed frame transition in each direction.
    # This is a heuristic and must never be represented as calibrated PSA grading.
    def boundary(profile,side):
        profile=np.convolve(profile,np.ones(7)/7,mode='same')
        dif=np.abs(np.gradient(profile.astype(float)))
        n=len(profile); lo=int(n*.025); hi=int(n*.22)
        if side=='end':
            pos, strength = boundary(profile[::-1], 'start')
            return n-1-pos, strength
        i=lo+int(np.argmax(dif[lo:hi])); strength=float(dif[i]);
        return i,strength
    # Ignore corners and use broad median strips to resist artwork and glare.
    px=np.median(g[150:690,:],axis=0); py=np.median(g[:,120:480],axis=1)
    l,sl=boundary(px,'start'); r,sr=boundary(px,'end'); t,st=boundary(py,'start'); b,sb=boundary(py,'end')
    left=float(l);right=float(599-r);top=float(t);bottom=float(839-b)
    def ratio(a,b): return [round(100*a/(a+b),1),round(100*b/(a+b),1)] if a+b>0 else None
    confidence='low' if min(sl,sr,st,sb)<3 or min(left,right,top,bottom)<5 else 'moderate'
    ok=(r>l and b>t and min(left,right,top,bottom)>=5)
    if not ok: confidence='low'
    import base64
    for x,y in [(l,0),(r,0)]: cv2.line(warp,(int(x),0),(int(x),839),(0,230,255),2)
    for x,y in [(0,t),(0,b)]: cv2.line(warp,(0,int(y)),(599,int(y)),(0,230,255),2)
    cv2.rectangle(warp,(0,0),(599,839),(70,240,100),3)
    _,buff=cv2.imencode('.jpg',warp,[cv2.IMWRITE_JPEG_QUALITY,85]); annotated='data:image/jpeg;base64,'+base64.b64encode(buff).decode()
    return {'horizontal':ratio(left,right),'vertical':ratio(top,bottom),'border_pixels':{'left':round(left,1),'right':round(right,1),'top':round(top,1),'bottom':round(bottom,1)},'confidence':confidence,'annotated':annotated,'warning':'Automated frame detection is heuristic. Verify yellow lines match the printed frame; full PSA grade cannot be determined reliably from these photos alone.'}

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

if __name__=='__main__': app.run(host='0.0.0.0',port=int(__import__('os').environ.get('PORT',5050)),debug=False)
