import {FormEvent,useState} from 'react';
import {Link,useNavigate} from 'react-router-dom';
import {ArrowRight,Code2,GitBranch,LockKeyhole,Mail,ShieldCheck,TerminalSquare} from 'lucide-react';
import {api} from '../lib/api';

export default function Register(){
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [confirm,setConfirm]=useState('');
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(false);
  const nav=useNavigate();

  async function submit(e:FormEvent){
    e.preventDefault();
    setError('');
    if(password!==confirm){setError('Passwords do not match.');return;}
    setLoading(true);
    try{
      await api.post('/auth/register',{email,password});
      nav('/login');
    }catch(err:any){
      const d=err.response?.data?.detail;
      setError(Array.isArray(d)?d.map((x:any)=>x.msg||'Validation error').join(', '):typeof d==='string'?d:'Unable to create account.');
    }finally{setLoading(false);}
  }

  const featureCards=[
    {Icon:Code2,title:'Understand',detail:'Ask about real repository context.'},
    {Icon:GitBranch,title:'Change',detail:'Generate focused, reviewable edits.'},
    {Icon:ShieldCheck,title:'Verify',detail:'Approve first, then run tests.'},
  ];

  return <main className="min-h-screen overflow-hidden bg-[#020604] text-white">
    <div className="relative mx-auto grid min-h-screen max-w-[1850px] lg:grid-cols-[minmax(0,1.25fr)_540px]">
      <section className="relative hidden overflow-hidden border-r border-[#153222] px-10 py-10 lg:flex xl:px-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_55%_42%,rgba(91,255,127,.11),transparent_30rem),radial-gradient(circle_at_8%_78%,rgba(186,255,98,.05),transparent_25rem)]"/>
        <div className="relative flex w-full flex-col">
          <div className="flex items-center gap-3">
            <div className="green-icon h-10 w-10 rounded-xl"><TerminalSquare size={18}/></div>
            <div><div className="font-semibold">GitHub AI Help</div><div className="font-mono text-[9px] uppercase tracking-[.18em] text-[#5c7665]">built for developers</div></div>
          </div>
          <div className="my-auto grid items-center gap-10 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="max-w-3xl">
              <div className="kicker">Your AI partner for every repository</div>
              <h1 className="mt-5 text-[clamp(4rem,5.8vw,7rem)] font-semibold leading-[.9] tracking-[-.07em]">Turn your codebase<br/><span className="bg-[linear-gradient(90deg,#f6fff8,#dfff9b_38%,#78ff92_75%,#5ef4c3)] bg-clip-text text-transparent">into a superpower.</span></h1>
              <p className="mt-7 max-w-2xl text-[18px] leading-8 text-[#819789]">Create your workspace, connect a repository, ask grounded questions, and turn engineering intent into reviewable code changes.</p>
              <div className="mt-9 grid max-w-2xl gap-3 sm:grid-cols-3">
                {featureCards.map(({Icon,title,detail})=><div key={title} className="green-card rounded-2xl p-4"><div className="green-icon h-9 w-9 rounded-xl"><Icon size={16}/></div><div className="mt-4 text-sm font-semibold">{title}</div><div className="mt-1 text-[11px] leading-5 text-[#6f8778]">{detail}</div></div>)}
              </div>
            </div>
            <div className="relative flex items-center justify-center"><div className="orb"><div className="orb-core"/></div></div>
          </div>
        </div>
      </section>

      <section className="relative flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,rgba(83,255,125,.07),transparent_24rem)]"/>
        <div className="relative w-full max-w-[430px] rounded-[26px] border border-[#25543a] bg-[#06100a]/92 p-6 shadow-[0_40px_120px_rgba(0,0,0,.48),0_0_90px_rgba(67,255,110,.05)] backdrop-blur-xl sm:p-8">
          <div className="mb-8 flex items-center gap-3 lg:hidden"><div className="green-icon h-9 w-9 rounded-xl"><TerminalSquare size={16}/></div><span className="font-semibold">GitHub AI Help</span></div>
          <div className="mb-8"><div className="kicker">Create account</div><h2 className="mt-3 text-[2.45rem] font-semibold tracking-[-.055em]">Create your workspace</h2><p className="mt-2 text-sm leading-6 text-[#789082]">Start exploring repositories with grounded AI assistance.</p></div>
          <form onSubmit={submit} className="space-y-5">
            <label className="block"><span className="mb-2 block text-xs font-medium text-[#c7d5cb]">Email address</span><div className="relative"><Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#557060]"/><input type="email" required className="field pl-11" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/></div></label>
            <label className="block"><span className="mb-2 block text-xs font-medium text-[#c7d5cb]">Password</span><div className="relative"><LockKeyhole size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#557060]"/><input type="password" minLength={8} required className="field pl-11" value={password} onChange={e=>setPassword(e.target.value)} placeholder="At least 8 characters"/></div></label>
            <label className="block"><span className="mb-2 block text-xs font-medium text-[#c7d5cb]">Confirm password</span><div className="relative"><LockKeyhole size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#557060]"/><input type="password" minLength={8} required className="field pl-11" value={confirm} onChange={e=>setConfirm(e.target.value)} placeholder="Repeat your password"/></div></label>
            {error&&<div className="rounded-xl border border-[#63313d] bg-[#231419] px-4 py-3 text-sm text-[#ffb4bf]">{error}</div>}
            <button disabled={loading} className="btn-primary w-full py-3.5">{loading?'Creating account…':'Create account'}{!loading&&<ArrowRight size={16}/>}</button>
          </form>
          <p className="mt-6 text-sm text-[#7d9183]">Already have an account? <Link to="/login" className="font-semibold text-[#dfff9b] hover:text-white">Sign in</Link></p>
        </div>
      </section>
    </div>
  </main>;
}