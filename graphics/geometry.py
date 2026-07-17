from __future__ import annotations
from math import hypot


def point_segment_distance(px,py,ax,ay,bx,by):
    dx=bx-ax; dy=by-ay; den=dx*dx+dy*dy
    if den<=1e-18: return hypot(px-ax,py-ay)
    t=max(0.0,min(1.0,((px-ax)*dx+(py-ay)*dy)/den))
    return hypot(px-(ax+t*dx),py-(ay+t*dy))


def point_in_polygon(x,y,poly):
    inside=False; j=len(poly)-1
    for i in range(len(poly)):
        xi,yi=poly[i]; xj,yj=poly[j]
        if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/(yj-yi+1e-30)+xi: inside=not inside
        j=i
    return inside
