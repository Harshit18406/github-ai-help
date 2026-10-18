import {useState,type ReactNode} from 'react';
import {Activity,LogOut,Search,TerminalSquare} from 'lucide-react';
import {Link,useLocation,useNavigate} from 'react-router-dom';

export default function Layout({children}:{children:ReactNode}){
 const nav=useNavigate();
 const location=useLocation();
 const [query,setQuery]=useState('');
 const email=localStorage.getItem('user_email')||'Workspace';
 const initials=email==='Workspace'?'AI':email.slice(0,2).toUpperCase();
 function submitSearch(e:React.FormEvent){e.preventDefault();const q=query.trim();if(!q)return;if(location.pathname==='/'){window.dispatchEvent(new CustomEvent('dashboard-search',{detail:q}));}else{nav(`/?q=${encodeURIComponent(q)}`)}}
 return <div className="min-h-screen text-[#f7fff8]">
  <header className="sticky top-0 z-50 h-[74px] border-b border-[#13301f] bg-[#020704]/92 backdrop-blur-2xl">
   <div className="flex h-full items-center gap-5 px-4 sm:px-6 lg:px-8">
    <Link to="/" className="flex min-w-fit items-center gap-3">
     <div className="brand-mark"><TerminalSquare size={18}/></div>
     <div><div className="text-[16px] font-semibold tracking-[-.035em]">GitHub AI Help</div><div className="hidden font-mono text-[8px] uppercase tracking-[.22em] text-[#56705f] sm:block">repository-aware agent</div></div>
    </Link>
    <form onSubmit={submitSearch} className="mx-auto hidden w-full max-w-[570px] md:block">
     <div className="top-search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search repositories, files, or ask anything..."/><span>Ctrl K</span></div>
    </form>
    <div className="ml-auto flex items-center gap-2 sm:gap-3">
     <div className="agent-pill hidden sm:flex"><Activity size={12}/><span className="dot"/><span>agent online</span></div>
     <div className="hidden items-center gap-2 rounded-xl border border-[#173724] bg-[#07110b] px-2.5 py-1.5 lg:flex"><div className="profile-orb">{initials}</div><div className="max-w-[150px] truncate text-xs font-medium text-[#dbe7de]">{email}</div></div>
     <button onClick={()=>{localStorage.clear();nav('/login')}} className="btn-ghost"><LogOut size={15}/><span className="hidden sm:inline">Sign out</span></button>
    </div>
   </div>
  </header>
  <main>{children}</main>
 </div>
}
