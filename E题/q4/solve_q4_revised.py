import os, json
import numpy as np, pandas as pd
from scipy.optimize import linprog, nnls

ROOT='/workspace/scratch/5d06d8aa380e'; SRC=f'{ROOT}/upload/附件1.xlsx'; CLS=f'{ROOT}/upload/6c8bf4f4-c5d7-4b31-969c-0cc87167eff7.xlsx'; OUT=os.environ.get('Q4_OUT',f'{ROOT}/q4_revised'); os.makedirs(OUT,exist_ok=True)
s1=pd.read_excel(SRC,'Sheet1'); s2=pd.read_excel(SRC,'Sheet2'); s3=pd.read_excel(SRC,'Sheet3')
for d in (s1,s2,s3): d.columns=d.columns.str.strip()
s1['日期']=pd.to_datetime(s1['日期']); s2['日期']=pd.to_datetime(s2['日期'])
for c in ['展现量','点击量','消费额','上方位展现量','上方首位展现量'] : s1[c]=pd.to_numeric(s1[c],errors='coerce').fillna(0)
for c in ['消费额','点击量','浏览量']: s3[c]=pd.to_numeric(s3[c],errors='coerce').fillna(0)
s1['单元键']=s1['方案ID'].astype(str)+'_'+s1['推广单元ID'].astype(str); s3['单元键']=s3['方案ID'].astype(str)+'_'+s3['推广单元ID'].astype(str)
s1['月份']=s1.日期.dt.month; s1['星期']=s1.日期.dt.dayofweek
s1['CPC']=np.where(s1.点击量>0,s1.消费额/s1.点击量,np.nan); s1['CTR']=np.where(s1.展现量>0,s1.点击量/s1.展现量,np.nan)
s1['展位']=np.where(s1.展现量>0,(s1.上方首位展现量+2.5*np.maximum(s1.上方位展现量-s1.上方首位展现量,0)+4*np.maximum(s1.展现量-s1.上方位展现量,0))/s1.展现量,np.nan)
daily=s1.groupby('日期').agg(消费额=('消费额','sum'),点击量=('点击量','sum'),展现量=('展现量','sum')).reset_index().merge(s2,on='日期'); daily['月份']=daily.日期.dt.month; daily['星期']=daily.日期.dt.dayofweek
targets=pd.date_range('2026-09-11','2026-09-17'); pu=pd.MultiIndex.from_product([targets,sorted(s1.单元键.unique())],names=['日期','单元键']).to_frame(index=False); pu['月份']=pu.日期.dt.month;pu['星期']=pu.日期.dt.dayofweek

def ridge(train,pred,ycol,transform='log',unit=True,r=.8):
    keys=(['单元键'] if unit else [])+['月份','星期']; tr=train[keys+[ycol]].dropna().copy()
    if transform=='log': tr=tr[tr[ycol]>0]; y=np.log(tr[ycol].to_numpy(float)); inv=np.exp
    elif transform=='logit':
        tr=tr[(tr[ycol]>0)&(tr[ycol]<1)]; z=np.clip(tr[ycol].to_numpy(float),1e-5,1-1e-5); y=np.log(z/(1-z)); inv=lambda a:1/(1+np.exp(-a))
    else: y=tr[ycol].to_numpy(float); inv=lambda a:a
    allx=pd.concat([tr[keys],pred[keys]],ignore_index=True).astype(str); X=pd.get_dummies(allx,columns=keys,dtype=float)
    xt=np.c_[np.ones(len(tr)),X.iloc[:len(tr)].to_numpy()]; xp=np.c_[np.ones(len(pred)),X.iloc[len(tr):].to_numpy()]
    pen=np.eye(xt.shape[1])*r;pen[0,0]=0;b=np.linalg.solve(xt.T@xt+pen,xt.T@y); fit=xt@b; pr=xp@b;res=y-fit; q=np.quantile(res,[.1,.9])
    return inv(pr),inv(pr+q[0]),inv(pr+q[1]),res

residuals={}
for col,tr in [('CPC','log'),('CTR','logit'),('展位','none')]:
    m,l,h,res=ridge(s1,pu,col,tr,True);pu[col+'预测']=m;pu[col+'下限']=np.minimum(l,h);pu[col+'上限']=np.maximum(l,h);residuals[col]=res
pu['CTR下限']=pu.CTR下限.clip(1e-4,.999);pu['CTR上限']=pu.CTR上限.clip(1e-4,.999);pu['展位预测']=pu.展位预测.clip(1,4);pu['展位下限']=pu.展位下限.clip(1,4);pu['展位上限']=pu.展位上限.clip(1,4)

# 0至2日非负分布滞后：注册由当日及前两日点击共同解释。
for k in range(3): daily[f'K{k}']=daily.点击量.shift(k)
lag=daily.dropna(subset=['K0','K1','K2','新注册数']).copy(); beta,_=nnls(lag[['K0','K1','K2']].to_numpy(float),lag.新注册数.to_numpy(float)); lag['基准注册']=lag[['K0','K1','K2']].to_numpy()@beta;lag['转化修正']=lag.新注册数/lag.基准注册
lag['转化修正']=lag.转化修正.clip(lag.转化修正.quantile(.01),lag.转化修正.quantile(.99))
rp=pd.DataFrame({'日期':targets});rp['月份']=rp.日期.dt.month;rp['星期']=rp.日期.dt.dayofweek
fm,fl,fh,fres=ridge(lag,rp,'转化修正','log',False,.5); rho0=beta.sum();rp['注册率预测']=rho0*fm;rp['注册率下限']=rho0*np.minimum(fl,fh);rp['注册率上限']=rho0*np.maximum(fl,fh)
pu=pu.merge(rp,on='日期')

# 同期校准仅用于CPC CTR和展位，权重0.50；注册率不再用异常的同期R/K校准。
ref=s1[s1.日期.between('2025-09-11','2025-09-17')].copy();ref['日期']=ref.日期+pd.DateOffset(years=1)
ref=ref[['日期','单元键','消费额','CPC','CTR','展位']].rename(columns={'消费额':'参考预算','CPC':'同期CPC','CTR':'同期CTR','展位':'同期展位'})
pu=pu.merge(ref,on=['日期','单元键'],how='left');pu['参考预算']=pu.参考预算.fillna(0); w=float(os.environ.get('Q4_BLEND','.50'))
for col,tr in [('CPC','log'),('CTR','logit')]:
    old=pu[col+'预测'].copy();a=pu['同期'+col]
    if tr=='log': new=np.exp(w*np.log(a.clip(1e-6))+(1-w)*np.log(old.clip(1e-6)))
    else:
        lg=lambda x:np.log(x.clip(1e-5,1-1e-5)/(1-x.clip(1e-5,1-1e-5)));iv=lambda z:1/(1+np.exp(-z));new=iv(w*lg(a)+(1-w)*lg(old))
    new=new.where(a.notna(),old);pu[col+'下限']=new*(pu[col+'下限']/old);pu[col+'上限']=new*(pu[col+'上限']/old);pu[col+'预测']=new
old=pu.展位预测.copy();new=(w*pu.同期展位+(1-w)*old).where(pu.同期展位.notna(),old);pu['展位下限']=(new+(pu.展位下限-old)).clip(1,4);pu['展位上限']=(new+(pu.展位上限-old)).clip(1,4);pu['展位预测']=new.clip(1,4)

# 直接读取问题二最终分类。
cl=pd.read_excel(CLS); long=cl.melt(id_vars=['方案ID','推广单元','序号'],value_vars=['黄金词','重点词','潜力词','问题词','无效词'],var_name='类型',value_name='关键词').dropna();long.关键词=long.关键词.astype(int)
s3=long.merge(s3,left_on=['方案ID','推广单元','关键词'],right_on=['方案ID','推广单元ID','关键词'],how='inner'); active=(s3.消费额>0)&(s3.点击量>0)
ug=s3.groupby('单元键').agg(单元消费=('消费额','sum'),单元点击=('点击量','sum'),单元浏览=('浏览量','sum')).reset_index();ug['qj']=ug.单元点击/ug.单元消费;ug['dj']=ug.单元浏览/ug.单元点击;s3=s3.merge(ug,on='单元键')
C0=float(os.environ.get('Q4_C0',s3.loc[s3.消费额>0,'消费额'].median()));s3['eta0']=((s3.点击量+s3.qj*C0)/(s3.消费额+C0))/s3.qj
candmask=active&s3.类型.isin(['黄金词','重点词','潜力词']);elo,ehi=s3.loc[candmask,'eta0'].quantile([.01,.99]);s3['eta']=s3.eta0.clip(elo,ehi);delta=float(os.environ.get('Q4_DELTA','.50'));s3['eta26']=1+delta*(s3.eta-1)
K0=float(s3.loc[s3.点击量>0,'点击量'].median());s3['depth']=(s3.浏览量+s3.dj*K0)/(s3.点击量+K0);dlo,dhi=s3.loc[candmask,'depth'].quantile([.1,.9])
s3['候选消费']=s3.消费额.where(candmask,0);den=s3.groupby('单元键').候选消费.transform('sum');s3['share']=np.where(den>0,s3.候选消费/den,0)

# 所有日期联合优化，总预算等于2025同期七日总额；单元日预算在同期85%至115%内。
blocks=[]
for _,u in pu[pu.参考预算>0].iterrows():
    z=s3[(s3.单元键==u.单元键)&candmask.loc[s3.index]].copy()
    if z.empty: continue
    for c in pu.columns: z[c]=u[c]
    z['cpc']=z.CPC预测/z.eta26;z['cpc_lo']=z.CPC下限/z.eta26;z['cpc_hi']=z.CPC上限/z.eta26
    z['obj_center']=z.注册率预测/z.cpc
    z['obj_robust']=z.注册率下限/z.cpc_hi
    blocks.append(z)
a=pd.concat(blocks,ignore_index=True);n=len(a);A=[];ub=[]
objective_type=os.environ.get('Q4_OBJECTIVE','center').strip().lower()
if objective_type not in {'center','robust'}: raise ValueError('Q4_OBJECTIVE must be center or robust')
a['obj']=a['obj_center'] if objective_type=='center' else a['obj_robust']
band=float(os.environ.get('Q4_BAND','.15'))
for (dt,key),idx in a.groupby(['日期','单元键']).groups.items():
    m=np.zeros(n);m[list(idx)]=1;B=float(a.loc[list(idx),'参考预算'].iloc[0]);A.extend([m,-m]);ub.extend([(1+band)*B,-(1-band)*B])
    pot=m*(a.类型.to_numpy()=='潜力词');beta_p=max(.15,float(a.loc[list(idx)&pd.Index([]),'share'].sum()) if False else float(a.loc[list(idx)][a.loc[list(idx),'类型']=='潜力词'].share.sum()));A.append(pot-beta_p*m);ub.append(0.)
gamma=float(os.environ.get('Q4_GAMMA','1.20'));cap_floor=float(os.environ.get('Q4_CAP_FLOOR','.05'))
caps=a.参考预算.to_numpy()*np.maximum(cap_floor,gamma*a.share.to_numpy());Btot=float(ref.参考预算.sum())
res=linprog(-a.obj.to_numpy(),A_ub=np.array(A),b_ub=np.array(ub),A_eq=[np.ones(n)],b_eq=[Btot],bounds=[(0,float(v)) for v in caps],method='highs')
if not res.success: raise RuntimeError(res.message)
a['投入金额']=res.x;a=a[a.投入金额>1e-7].copy();a['预期点击量']=a.投入金额/a.cpc;a['预期展现量']=a.预期点击量/a.CTR预测;a['预期浏览量']=a.预期点击量*a.depth;a['预期注册量']=a.预期点击量*a.注册率预测
a['竞价下限']=a.cpc_lo;a['竞价上限']=a.cpc_hi

# 残差Bootstrap：对每次模拟同时扰动CPC CTR和注册率，取总量10%和90%分位数。
rng=np.random.default_rng(20260912);S=2000;sim=[]
cpc_res=np.asarray(residuals['CPC']);cpc_res=cpc_res-np.log(np.mean(np.exp(cpc_res)))
ctr_res=np.asarray(residuals['CTR']);ctr_res=ctr_res-np.median(ctr_res)
fres=np.asarray(fres);fres=fres-np.log(np.mean(np.exp(fres)))
for q in range(S):
    cm=np.exp(rng.choice(cpc_res,len(a)));zm=rng.choice(ctr_res,len(a));rm=np.exp(rng.choice(fres,len(a)))
    click=a.预期点击量.to_numpy()/cm; ctr0=a.CTR预测.to_numpy();lg=np.log(ctr0/(1-ctr0))+zm;ct=1/(1+np.exp(-lg));reg=click*a.注册率预测.to_numpy()*rm
    z=pd.DataFrame({'日期':a.日期.to_numpy(),'展现':click/ct,'点击':click,'浏览':click*a.depth.to_numpy(),'注册':reg}).groupby('日期').sum();z['模拟']=q;sim.append(z.reset_index())
sim=pd.concat(sim)
# 将模拟总体中位数校准到中心预测，避免对数残差反变换造成系统性偏移。
cent={'展现':a.预期展现量.sum(),'点击':a.预期点击量.sum(),'浏览':a.预期浏览量.sum(),'注册':a.预期注册量.sum()}
st=sim.groupby('模拟')[['展现','点击','浏览','注册']].sum()
for m in cent: sim[m]*=cent[m]/st[m].median()
st2=sim.groupby('模拟')[['展现','点击','浏览','注册']].sum()
total_intervals={m:[float(st2[m].quantile(.1)),float(st2[m].quantile(.9))] for m in ['展现','点击','浏览','注册']}
qs=sim.groupby('日期')[['展现','点击','浏览','注册']].quantile([.1,.9]).unstack();qs.columns=[f'{x}_{"下限" if y==.1 else "上限"}' for x,y in qs.columns];qs=qs.reset_index()
summary=a.groupby('日期').agg(投入金额=('投入金额','sum'),词数=('关键词','count'),预期展现=('预期展现量','sum'),预期点击=('预期点击量','sum'),预期浏览=('预期浏览量','sum'),预期注册=('预期注册量','sum')).reset_index().merge(qs,on='日期');summary['注册成本']=summary.投入金额/summary.预期注册
# 关键词级经验范围：以CPC、CTR、展位和注册率的10%至90%边界组合计算。
a['竞价代理值']=a.cpc;a['竞价下限']=a.cpc_lo;a['竞价上限']=a.cpc_hi
a['展现量下限']=(a.投入金额/a.cpc_hi)/a.CTR上限
a['展现量上限']=(a.投入金额/a.cpc_lo)/a.CTR下限
a['点击量下限']=a.投入金额/a.cpc_hi;a['点击量上限']=a.投入金额/a.cpc_lo
a['浏览量下限']=a.点击量下限*a.depth;a['浏览量上限']=a.点击量上限*a.depth
a['注册量下限']=a.点击量下限*a.注册率下限;a['注册量上限']=a.点击量上限*a.注册率上限
a.to_csv(f'{OUT}/plan.csv',index=False,encoding='utf-8-sig');summary.to_csv(f'{OUT}/summary.csv',index=False,encoding='utf-8-sig');pu.to_csv(f'{OUT}/unit_predictions.csv',index=False,encoding='utf-8-sig')
out={'objective_type':objective_type,'C0':C0,'K0':K0,'delta':delta,'blend':w,'band':band,'gamma':gamma,'cap_floor':cap_floor,'eta_bounds':[float(elo),float(ehi)],'lag_beta':beta.tolist(),'lag_total':float(beta.sum()),'budget':Btot,'rows':len(a),'totals':{c:float(summary[c].sum()) for c in ['投入金额','预期展现','预期点击','预期浏览','预期注册']},'total_intervals':total_intervals,'reg_interval':total_intervals['注册']}
json.dump(out,open(f'{OUT}/results.json','w'),ensure_ascii=False,indent=2);print(json.dumps(out,ensure_ascii=False,indent=2));print(summary.to_string(index=False))
