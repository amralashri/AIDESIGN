from __future__ import annotations

def point_in_rect(point,rect):
    x,y=point
    xmin,ymin,xmax,ymax=rect
    return xmin<=x<=xmax and ymin<=y<=ymax

def segment_intersects_rectangle(a,b,rect):
    if point_in_rect(a,rect) or point_in_rect(b,rect):
        return True
    xmin,ymin,xmax,ymax=rect
    edges=[
        ((xmin,ymin),(xmax,ymin)),
        ((xmax,ymin),(xmax,ymax)),
        ((xmax,ymax),(xmin,ymax)),
        ((xmin,ymax),(xmin,ymin)),
    ]
    def orientation(p,q,r):
        value=(q[1]-p[1])*(r[0]-q[0])-(q[0]-p[0])*(r[1]-q[1])
        if abs(value)<1e-9:return 0
        return 1 if value>0 else 2
    def intersect(p1,q1,p2,q2):
        o1=orientation(p1,q1,p2)
        o2=orientation(p1,q1,q2)
        o3=orientation(p2,q2,p1)
        o4=orientation(p2,q2,q1)
        return o1!=o2 and o3!=o4
    return any(intersect(a,b,c,d) for c,d in edges)
