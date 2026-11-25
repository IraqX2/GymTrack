import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, clearAccessToken, exportCsv, login, logout, restoreSession, signup, type GymRow, type GymUser } from "./services/gymtrack";

type Field = { key: string; label: string; type?: string; options?: string[]; required?: boolean };
type Module = { title: string; path: string; fields: Field[]; columns: string[]; adminOnly?: boolean; create?: boolean; edit?: boolean; remove?: boolean };

const modules: Record<string, Module> = {
  Members: {
    title: "Members", path: "/api/members", adminOnly: true, create: true, edit: true, remove: true,
    fields: [
      { key: "full_name", label: "Full name", required: true },
      { key: "email", label: "Email", type: "email", required: true },
      { key: "phone", label: "Phone" },
      { key: "join_date", label: "Join date", type: "date", required: true },
      { key: "is_active", label: "Active member", type: "checkbox" },
    ],
    columns: ["full_name", "email", "phone", "join_date", "is_active"],
  },
  Trainers: {
    title: "Trainers", path: "/api/trainers", adminOnly: true, create: true, edit: true, remove: true,
    fields: [
      { key: "full_name", label: "Full name", required: true },
      { key: "email", label: "Email", type: "email", required: true },
      { key: "phone", label: "Phone" },
      { key: "specialization", label: "Specialization" },
      { key: "is_active", label: "Active trainer", type: "checkbox" },
    ],
    columns: ["full_name", "email", "phone", "specialization", "is_active"],
  },
  Memberships: {
    title: "Memberships", path: "/api/memberships", create: true, edit: true, remove: true, adminOnly: true,
    fields: [
      { key: "member_id", label: "Member ID", type: "number", required: true },
      { key: "plan_name", label: "Plan name", required: true },
      { key: "start_date", label: "Start date", type: "date", required: true },
      { key: "end_date", label: "End date", type: "date", required: true },
      { key: "price", label: "Price", type: "number", required: true },
      { key: "status", label: "Status", type: "select", options: ["active", "expired", "cancelled"] },
    ],
    columns: ["member_id", "plan_name", "start_date", "end_date", "price", "status"],
  },
  Attendance: {
    title: "Attendance", path: "/api/attendance", create: true, adminOnly: true,
    fields: [
      { key: "member_id", label: "Member ID", type: "number", required: true },
      { key: "notes", label: "Notes" },
    ],
    columns: ["member_id", "check_in", "check_out", "notes"],
  },
  "Workout Plans": {
    title: "Workout Plans", path: "/api/workout-plans", create: true, edit: true, remove: true, adminOnly: true,
    fields: [
      { key: "title", label: "Plan title", required: true },
      { key: "description", label: "Description", type: "textarea" },
      { key: "level", label: "Level", type: "select", options: ["beginner", "intermediate", "advanced"] },
      { key: "duration_weeks", label: "Duration (weeks)", type: "number" },
    ],
    columns: ["title", "level", "duration_weeks", "created_at"],
  },
};

const navAdmin = ["Overview", "Members", "Trainers", "Memberships", "Attendance", "Workout Plans", "Groups", "Administration", "Profile"];
const navUser = ["Overview", "Memberships", "Attendance", "Workout Plans", "Groups", "Profile"];
const icons: Record<string, string> = { Overview: "▦", Members: "♙", Trainers: "♧", Memberships: "▤", Attendance: "◷", "Workout Plans": "⌁", Groups: "◎", Administration: "⚙", Profile: "◉" };

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase();
}
function fmt(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Active" : "Inactive";
  if (typeof value === "object") return new Date(String(value)).toLocaleString();
  return String(value);
}
function defaults(fields: Field[]) {
  const values: Record<string, unknown> = {};
  fields.forEach(field => {
    if (field.type === "checkbox") values[field.key] = true;
    else if (field.type === "select") values[field.key] = field.options?.[0] ?? "";
    else if (field.type === "date") values[field.key] = new Date().toISOString().slice(0, 10);
    else if (field.type === "number") values[field.key] = 0;
    else values[field.key] = "";
  });
  return values;
}

function LoginScreen({ onLogin }: { onLogin: (user: GymUser) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const user = mode === "login"
        ? await login(email, password)
        : await signup(fullName, email, password);
      onLogin(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not authenticate");
    } finally { setBusy(false); }
  }
  return <div className="gt-auth-screen">
    <section className="gt-auth-brand">
      <div className="gt-brand-lockup"><span className="gt-logo">GT</span><strong>GymTrack</strong></div>
      <span className="gt-auth-kicker">YOUR GYM, ORGANIZED</span>
      <h1>Build stronger routines.<br/><em>Run a smarter gym.</em></h1>
      <p>One secure workspace for members, trainers, memberships, attendance and workout plans.</p>
      <div className="gt-auth-points"><span>✓ Member management</span><span>✓ Training & attendance</span><span>✓ Secure team access</span></div>
    </section>
    <section className="gt-auth-card">
      <div className="gt-auth-card-head"><span className="gt-eyebrow">GYMTRACK WORKSPACE</span><div className="gt-tabs"><button className={mode==="login"?"active":""} onClick={()=>{setMode("login");setError("");}}>Sign in</button><button className={mode==="signup"?"active":""} onClick={()=>{setMode("signup");setError("");}}>Sign up</button></div></div>
      <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
      <p className="gt-muted">{mode === "login" ? "Enter your account details to continue." : "Register a member profile to get started."}</p>
      <form onSubmit={submit} className="gt-auth-form">
        {mode==="signup" && <label>Full name<input value={fullName} onChange={e=>setFullName(e.target.value)} required minLength={2} autoComplete="name"/></label>}
        <label>Email address<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required autoComplete="username"/></label>
        <label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={mode==="signup"?8:1} autoComplete={mode==="login"?"current-password":"new-password"}/></label>
        {error && <div className="gt-alert error">{error}</div>}
        <button className="gt-primary gt-full" disabled={busy}>{busy ? "Please wait…" : mode==="login"?"Sign in":"Create account"}</button>
      </form>
      <p className="gt-auth-switch">{mode==="login"?"New to GymTrack?":"Already have an account?"} <button onClick={()=>{setMode(mode==="login"?"signup":"login");setError("");}}>{mode==="login"?"Create account":"Sign in"}</button></p>
      <div className="gt-auth-safe"><span>🔒</span> Protected session · Secure password storage · Role-based access</div>
    </section>
  </div>;
}

function Overview({ user }: { user: GymUser }) {
  const [stats, setStats] = useState<Record<string, number>>({});
  const [memberships, setMemberships] = useState<GymRow[]>([]);
  const [assignments, setAssignments] = useState<GymRow[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    if (user.role === "admin") api<Record<string, number>>("/api/admin/stats").then(value=>live&&setStats(value)).catch(err=>live&&setError(err.message));
    else Promise.all([api<GymRow[]>("/api/memberships"), api<GymRow[]>("/api/workout-assignments")])
      .then(([m,a])=>{if(live){setMemberships(m);setAssignments(a);}}).catch(err=>live&&setError(err.message));
    return ()=>{live=false;};
  }, [user.role]);
  const cards = user.role==="admin" ? [
    ["Users",stats.users],["Admins",stats.admins],["Banned users",stats.banned_users],["New users (7 days)",stats.new_users_7d],
    ["Members",stats.members],["Active members",stats.active_members],["Trainers",stats.trainers],["Memberships",stats.memberships],
    ["Today's attendance",stats.attendance_today],["Workout plans",stats.workout_plans],["Groups",stats.groups],
  ] : [["My memberships",memberships.length],["Assigned workouts",assignments.length]];
  return <div className="gt-page-stack">
    <section className="gt-welcome"><div><p className="gt-eyebrow">GYMTRACK OVERVIEW</p><h2>Good {new Date().getHours()<12?"morning":new Date().getHours()<18?"afternoon":"evening"}, {user.full_name.split(" ")[0]}</h2><p>{user.role==="admin"?"Manage gym operations and keep your team moving.":"Your memberships and training information in one place."}</p></div><span className="gt-role-tag">{user.role.toUpperCase()}</span></section>
    {error&&<div className="gt-alert error">{error}</div>}
    <section className="gt-stat-grid">{cards.map(([label,value])=><article className="gt-stat" key={label}><span>{label}</span><strong>{value??"—"}</strong></article>)}</section>
    {user.role==="admin" ? <section className="gt-panel"><p className="gt-eyebrow">OPERATIONS</p><h3>Gym management workspace</h3><p className="gt-muted">Use the navigation to manage members, trainers, memberships, attendance, workout plans, teams and administrator activity.</p></section> :
      <div className="gt-two-col"><section className="gt-panel"><p className="gt-eyebrow">MEMBERSHIP</p><h3>My memberships</h3>{memberships.length?memberships.map(row=><div className="gt-simple-row" key={row.id}><strong>{row.plan_name}</strong><span>{row.status} · ends {row.end_date}</span></div>):<p className="gt-empty">No membership linked to your account yet.</p>}</section>
      <section className="gt-panel"><p className="gt-eyebrow">TRAINING</p><h3>My assigned workouts</h3>{assignments.length?assignments.map(row=><div className="gt-simple-row" key={row.id}><strong>Workout assignment #{row.id}</strong><span>{row.status}</span></div>):<p className="gt-empty">No workout assignment yet.</p>}</section></div>}
  </div>;
}

function DataModule({ name, user }: { name: string; user: GymUser }) {
  const spec=modules[name];
  const [rows,setRows]=useState<GymRow[]>([]);
  const [form,setForm]=useState<Record<string,unknown>>(()=>defaults(spec.fields));
  const [editing,setEditing]=useState<GymRow|null>(null);
  const [show,setShow]=useState(false);
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const admin=user.role==="admin";
  const load=useCallback(async()=>{setLoading(true);try{setRows(await api<GymRow[]>(spec.path));setError("");}catch(e){setError(e instanceof Error?e.message:"Could not load data");}finally{setLoading(false);}},[spec.path]);
  useEffect(()=>{void load();},[load]);
  function create(){setEditing(null);setForm(defaults(spec.fields));setShow(true);setError("");setMessage("");}
  function edit(row:GymRow){const next=defaults(spec.fields);spec.fields.forEach(field=>{if(row[field.key]!==undefined&&row[field.key]!==null)next[field.key]=row[field.key];});setEditing(row);setForm(next);setShow(true);setError("");setMessage("");}
  async function save(event:FormEvent){event.preventDefault();setSaving(true);setError("");try{await api(editing?spec.path+"/"+editing.id:spec.path,editing?(name==="Memberships"?"PATCH":"PUT"):"POST",form);setMessage(editing?"Record updated.":"Record created.");setShow(false);setEditing(null);await load();}catch(e){setError(e instanceof Error?e.message:"Could not save record");}finally{setSaving(false);}}
  async function remove(row:GymRow){if(!window.confirm("Delete this record?"))return;try{await api(spec.path+"/"+row.id,"DELETE");setMessage("Record deleted.");await load();}catch(e){setError(e instanceof Error?e.message:"Could not delete record");}}
  async function checkOut(row:GymRow){try{await api("/api/attendance/"+row.id+"/checkout","PATCH");setMessage("Member checked out.");await load();}catch(e){setError(e instanceof Error?e.message:"Could not check out");}}
  return <div className="gt-page-stack">
    <section className="gt-section-title"><div><p className="gt-eyebrow">GYM OPERATIONS</p><h2>{name}</h2><p className="gt-muted">{admin?"Manage your gym's "+name.toLowerCase()+".":"View records linked to your account."}</p></div>{admin&&spec.create&&<button className="gt-primary" onClick={create}>+ Add {name==="Workout Plans"?"plan":name==="Attendance"?"check-in":name.slice(0,-1)}</button>}</section>
    {message&&<div className="gt-alert success">{message}</div>}{error&&<div className="gt-alert error">{error}</div>}
    {show&&<section className="gt-panel"><div className="gt-panel-head"><h3>{editing?"Edit":"Add"} {name==="Workout Plans"?"workout plan":name.slice(0,-1)}</h3><button className="gt-secondary" type="button" onClick={()=>setShow(false)}>Close</button></div>
      <form className="gt-form-grid" onSubmit={save}>{spec.fields.map(field=><label className={field.type==="checkbox"?"gt-checkbox-field":"gt-field"} key={field.key}>{field.type==="checkbox"?<><input type="checkbox" checked={Boolean(form[field.key])} onChange={e=>setForm(old=>({...old,[field.key]:e.target.checked}))}/>{field.label}</>:<>{field.label}{field.type==="select"?<select value={String(form[field.key]??"")} onChange={e=>setForm(old=>({...old,[field.key]:e.target.value}))}>{field.options?.map(x=><option value={x} key={x}>{x}</option>)}</select>:field.type==="textarea"?<textarea rows={3} value={String(form[field.key]??"")} onChange={e=>setForm(old=>({...old,[field.key]:e.target.value}))}/>:<input type={field.type||"text"} value={String(form[field.key]??"")} required={field.required!==false} onChange={e=>setForm(old=>({...old,[field.key]:field.type==="number"?Number(e.target.value):e.target.value}))}/>}</>}</label>)}
      <div className="gt-form-actions"><button className="gt-primary" disabled={saving}>{saving?"Saving…":"Save record"}</button><button type="button" className="gt-secondary" onClick={()=>setShow(false)}>Cancel</button></div></form>
    </section>}
    <section className="gt-panel"><div className="gt-panel-head"><div><p className="gt-eyebrow">RECORD DIRECTORY</p><h3>{name} ({rows.length})</h3></div><button className="gt-secondary" onClick={()=>void load()}>Refresh</button></div>
      {loading?<p className="gt-empty">Loading records…</p>:!rows.length?<div className="gt-empty-state"><strong>No {name.toLowerCase()} yet</strong><p>Records saved in this module will appear here.</p></div>:
      <div className="gt-table-wrap"><table className="gt-table"><thead><tr>{spec.columns.map(key=><th key={key}>{key.replaceAll("_"," ")}</th>)}<th>ID</th>{(admin&&(spec.edit||spec.remove)||name==="Attendance"&&admin)&&<th>Actions</th>}</tr></thead><tbody>{rows.map(row=><tr key={row.id}>{spec.columns.map(key=><td key={key}>{key==="is_active"?<span className={row[key]?"gt-status active":"gt-status"}>{row[key]?"Active":"Inactive"}</span>:showValue(row[key])}</td>)}<td>#{row.id}</td>{admin&&(spec.edit||spec.remove||name==="Attendance")&&<td><div className="gt-actions">{spec.edit&&<button onClick={()=>edit(row)}>Edit</button>}{name==="Attendance"&&!row.check_out&&<button onClick={()=>void checkOut(row)}>Check out</button>}{spec.remove&&<button className="danger" onClick={()=>void remove(row)}>Delete</button>}</div></td>}</tr>)}</tbody></table></div>}
    </section>
    {name==="Workout Plans"&&admin&&<Assignments/>}
  </div>;
}
function showValue(value:unknown){if(value===null||value===undefined||value==="")return "—";if(typeof value==="boolean")return value?"Yes":"No";if(typeof value==="object")return new Date(String(value)).toLocaleString();return String(value);}

function Assignments(){
  const [items,setItems]=useState<GymRow[]>([]),[plans,setPlans]=useState<GymRow[]>([]),[members,setMembers]=useState<GymRow[]>([]),[trainers,setTrainers]=useState<GymRow[]>([]);
  const [form,setForm]=useState({plan_id:0,member_id:0,trainer_id:0,start_date:new Date().toISOString().slice(0,10),status:"active"});
  const [error,setError]=useState("");
  const load=useCallback(async()=>{try{const [a,p,m,t]=await Promise.all([api<GymRow[]>("/api/workout-assignments"),api<GymRow[]>("/api/workout-plans"),api<GymRow[]>("/api/members"),api<GymRow[]>("/api/trainers")]);setItems(a);setPlans(p);setMembers(m);setTrainers(t);setForm(old=>({...old,plan_id:old.plan_id||p[0]?.id||0,member_id:old.member_id||m[0]?.id||0}));}catch(e){setError(e instanceof Error?e.message:"Could not load assignments");}},[]);
  useEffect(()=>{void load();},[load]);
  async function add(event:FormEvent){event.preventDefault();setError("");try{await api("/api/workout-assignments","POST",{...form,trainer_id:form.trainer_id||null});await load();}catch(e){setError(e instanceof Error?e.message:"Could not assign workout");}}
  async function remove(id:number){if(!window.confirm("Remove this workout assignment?"))return;try{await api("/api/workout-assignments/"+id,"DELETE");await load();}catch(e){setError(e instanceof Error?e.message:"Could not remove assignment");}}
  return <section className="gt-panel"><p className="gt-eyebrow">WORKOUT ALLOCATION</p><h3>Assign a plan to a member</h3>{error&&<div className="gt-alert error">{error}</div>}
    {!plans.length||!members.length?<p className="gt-empty">Create at least one plan and one member before assigning a workout.</p>:<form className="gt-form-grid" onSubmit={add}>
      <label className="gt-field">Plan<select value={form.plan_id} onChange={e=>setForm({...form,plan_id:Number(e.target.value)})}>{plans.map(x=><option key={x.id} value={x.id}>{x.title}</option>)}</select></label>
      <label className="gt-field">Member<select value={form.member_id} onChange={e=>setForm({...form,member_id:Number(e.target.value)})}>{members.map(x=><option key={x.id} value={x.id}>{x.full_name} (#{x.id})</option>)}</select></label>
      <label className="gt-field">Trainer<select value={form.trainer_id} onChange={e=>setForm({...form,trainer_id:Number(e.target.value)})}><option value={0}>No trainer</option>{trainers.map(x=><option key={x.id} value={x.id}>{x.full_name}</option>)}</select></label>
      <label className="gt-field">Start date<input type="date" value={form.start_date} onChange={e=>setForm({...form,start_date:e.target.value})}/></label>
      <div className="gt-form-actions"><button className="gt-primary">Assign plan</button></div>
    </form>}
    <div className="gt-table-wrap"><table className="gt-table"><thead><tr><th>ID</th><th>Plan</th><th>Member</th><th>Status</th><th></th></tr></thead><tbody>{items.map(x=><tr key={x.id}><td>#{x.id}</td><td>{x.plan_id}</td><td>{x.member_id}</td><td>{x.status}</td><td><button className="danger" onClick={()=>void remove(x.id)}>Remove</button></td></tr>)}</tbody></table></div>
  </section>;
}

function GroupsPage(){
  const [groups,setGroups]=useState<GymRow[]>([]),[selected,setSelected]=useState<GymRow|null>(null),[members,setMembers]=useState<GymRow[]>([]),[work,setWork]=useState<GymRow[]>([]);
  const [name,setName]=useState(""),[email,setEmail]=useState(""),[title,setTitle]=useState("");
  const [grants,setGrants]=useState({can_create:true,can_edit:true,can_assign:false}),[assigned,setAssigned]=useState(0),[error,setError]=useState(""),[message,setMessage]=useState("");
  const loadGroups=useCallback(async()=>{try{setGroups(await api<GymRow[]>("/api/groups"));}catch(e){setError(e instanceof Error?e.message:"Could not load groups");}},[]);
  const loadDetail=useCallback(async(group:GymRow)=>{setSelected(group);try{const [m,w]=await Promise.all([api<GymRow[]>("/api/groups/"+group.id+"/members"),api<GymRow[]>("/api/groups/"+group.id+"/work")]);setMembers(m);setWork(w);}catch(e){setError(e instanceof Error?e.message:"Could not load group details");}},[]);
  useEffect(()=>{void loadGroups();},[loadGroups]);
  async function create(event:FormEvent){event.preventDefault();try{await api("/api/groups","POST",{name});setName("");setMessage("Group created.");await loadGroups();}catch(e){setError(e instanceof Error?e.message:"Could not create group");}}
  async function renameSelected(){if(!selected)return;const next=window.prompt("New group name",selected.name);if(next===null||next.trim().length<2)return;try{await api("/api/groups/"+selected.id,"PATCH",{name:next.trim()});const updated={...selected,name:next.trim()};await loadGroups();await loadDetail(updated);}catch(e){setError(e instanceof Error?e.message:"Could not rename group");}}
  async function deleteSelected(){if(!selected||!window.confirm("Delete this group and its shared work?"))return;try{await api("/api/groups/"+selected.id,"DELETE");setSelected(null);setMembers([]);setWork([]);await loadGroups();setMessage("Group deleted.");}catch(e){setError(e instanceof Error?e.message:"Could not delete group");}}
  async function invite(event:FormEvent){event.preventDefault();if(!selected)return;try{await api("/api/groups/"+selected.id+"/members","POST",{email,...grants});setEmail("");setMessage("Group member added.");await loadDetail(selected);}catch(e){setError(e instanceof Error?e.message:"Could not add user");}}
  async function permission(row:GymRow,key:"can_create"|"can_edit"|"can_assign"){if(!selected)return;try{await api("/api/groups/"+selected.id+"/members/"+row.user_id,"PATCH",{can_create:key==="can_create"?!row.can_create:row.can_create,can_edit:key==="can_edit"?!row.can_edit:row.can_edit,can_assign:key==="can_assign"?!row.can_assign:row.can_assign});await loadDetail(selected);}catch(e){setError(e instanceof Error?e.message:"Could not change permission");}}
  async function removeMember(row:GymRow){if(!selected||!window.confirm("Remove this member?"))return;try{await api("/api/groups/"+selected.id+"/members/"+row.user_id,"DELETE");await loadDetail(selected);}catch(e){setError(e instanceof Error?e.message:"Could not remove member");}}
  async function addWork(event:FormEvent){event.preventDefault();if(!selected)return;try{await api("/api/groups/"+selected.id+"/work","POST",{title,assigned_to:assigned||null});setTitle("");setAssigned(0);await loadDetail(selected);}catch(e){setError(e instanceof Error?e.message:"Could not create team task");}}
  async function toggle(row:GymRow){if(!selected)return;try{await api("/api/groups/"+selected.id+"/work/"+row.id,"PATCH",{is_completed:!row.is_completed});await loadDetail(selected);}catch(e){setError(e instanceof Error?e.message:"Could not update task");}}
  async function deleteWork(row:GymRow){if(!selected||!window.confirm("Delete this group task?"))return;try{await api("/api/groups/"+selected.id+"/work/"+row.id,"DELETE");await loadDetail(selected);}catch(e){setError(e instanceof Error?e.message:"Could not delete task");}}
  return <div className="gt-page-stack"><section className="gt-section-title"><div><p className="gt-eyebrow">TEAM WORKSPACE</p><h2>Groups</h2><p className="gt-muted">Share operational work with members and staff using permissions.</p></div></section>
    {error&&<div className="gt-alert error">{error}</div>}{message&&<div className="gt-alert success">{message}</div>}
    <div className="gt-two-col"><section className="gt-panel"><h3>Create a group</h3><form className="gt-inline-form" onSubmit={create}><input value={name} onChange={e=>setName(e.target.value)} placeholder="New group name" required minLength={2}/><button className="gt-primary">Create group</button></form><h3 className="gt-subheading">Your groups</h3>{groups.length?groups.map(g=><button className={selected?.id===g.id?"gt-group-choice selected":"gt-group-choice"} key={g.id} onClick={()=>void loadDetail(g)}><span><strong>{g.name}</strong><small>Group #{g.id}</small></span><em>{g.my_role}</em></button>):<p className="gt-empty">No group joined yet.</p>}</section>
      <section className="gt-panel">{!selected?<div className="gt-empty-state"><strong>Select a group</strong><p>Choose a team to see its members and shared work.</p></div>:<>
        <div className="gt-panel-head"><div><p className="gt-eyebrow">SELECTED TEAM</p><h3>{selected.name}</h3></div><div className="gt-panel-tools"><span className="gt-role-tag">{selected.my_role}</span>{selected.my_role==="owner"&&<><button className="gt-secondary" onClick={()=>void renameSelected()}>Rename</button><button className="gt-danger-outline" onClick={()=>void deleteSelected()}>Delete group</button></>}</div></div>
        <h4>Members and permissions</h4>{members.map(row=><div className="gt-member-row" key={row.user_id}><div><strong>{row.full_name}</strong><small>{row.email} · {row.role}</small></div>{row.role==="owner"?<span className="gt-status active">Owner</span>:<div className="gt-permissions">{(["can_create","can_edit","can_assign"] as const).map(key=><label key={key}><input type="checkbox" checked={Boolean(row[key])} onChange={()=>void permission(row,key)}/>{key.replace("can_","")}</label>)}<button className="danger" onClick={()=>void removeMember(row)}>Remove</button></div>}</div>)}
        {selected.my_role==="owner"&&<form className="gt-invite-form" onSubmit={invite}><h4>Add a registered user</h4><input type="email" placeholder="User email" value={email} onChange={e=>setEmail(e.target.value)} required/><div className="gt-permissions">{(["can_create","can_edit","can_assign"] as const).map(key=><label key={key}><input type="checkbox" checked={grants[key]} onChange={e=>setGrants(old=>({...old,[key]:e.target.checked}))}/>{key.replace("can_","")}</label>)}</div><button className="gt-primary">Add member</button></form>}
        <h4 className="gt-subheading">Shared team work</h4><form className="gt-inline-form" onSubmit={addWork}><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Task or duty" required/><select value={assigned} onChange={e=>setAssigned(Number(e.target.value))}><option value={0}>Unassigned</option>{members.map(row=><option value={row.user_id} key={row.user_id}>{row.full_name}</option>)}</select><button className="gt-primary">Add</button></form>
        {work.map(row=><div className="gt-work-row" key={row.id}><label><input type="checkbox" checked={row.is_completed} onChange={()=>void toggle(row)}/><span className={row.is_completed?"completed":""}>{row.title}</span></label><small>{members.find(m=>m.user_id===row.assigned_to)?.full_name||"Unassigned"}</small>{selected.my_role==="owner"&&<button className="danger" onClick={()=>void deleteWork(row)}>Delete</button>}</div>)}
      </>}</section></div>
  </div>;
}

function Administration(){
  const [tab,setTab]=useState<"Users"|"Activity"|"Security">("Users");
  const [users,setUsers]=useState<GymRow[]>([]),[logs,setLogs]=useState<GymRow[]>([]);
  const [security,setSecurity]=useState<{failed_logins_24h:number;events:GymRow[]}>({failed_logins_24h:0,events:[]});
  const [query,setQuery]=useState(""),[error,setError]=useState("");
  const load=useCallback(async()=>{try{if(tab==="Users")setUsers(await api<GymRow[]>("/api/admin/users?q="+encodeURIComponent(query)));if(tab==="Activity")setLogs(await api<GymRow[]>("/api/admin/activity?q="+encodeURIComponent(query)));if(tab==="Security")setSecurity(await api("/api/admin/security"));setError("");}catch(e){setError(e instanceof Error?e.message:"Could not load admin information");}},[tab,query]);
  useEffect(()=>{void load();},[load]);
  async function changeRole(row:GymRow){const next=row.role==="admin"?"user":"admin";if(!window.confirm("Change "+row.email+" to "+next+"?"))return;try{await api("/api/admin/users/"+row.id+"/role","PATCH",{role:next});await load();}catch(e){setError(e instanceof Error?e.message:"Could not change role");}}
  async function ban(row:GymRow){if(row.is_banned){try{await api("/api/admin/users/"+row.id+"/unban","POST");await load();}catch(e){setError(e instanceof Error?e.message:"Could not unban user");}return;}const reason=window.prompt("Ban reason:");if(reason===null)return;try{await api("/api/admin/users/"+row.id+"/ban","POST",{reason});await load();}catch(e){setError(e instanceof Error?e.message:"Could not ban user");}}
  async function revoke(row:GymRow){if(!window.confirm("Revoke all sessions for "+row.email+"?"))return;try{await api("/api/admin/users/"+row.id+"/revoke-sessions","POST");}catch(e){setError(e instanceof Error?e.message:"Could not revoke sessions");}}
  return <div className="gt-page-stack"><section className="gt-section-title"><div><p className="gt-eyebrow">SYSTEM CONTROL</p><h2>Administration</h2><p className="gt-muted">Manage accounts, review activity and monitor security.</p></div></section>
    <div className="gt-tabbar">{(["Users","Activity","Security"] as const).map(item=><button className={tab===item?"active":""} key={item} onClick={()=>setTab(item)}>{item}</button>)}</div>
    {error&&<div className="gt-alert error">{error}</div>}
    <section className="gt-panel"><div className="gt-panel-head"><h3>{tab}</h3><div className="gt-panel-tools">{tab!=="Security"&&<input placeholder="Search" value={query} onChange={e=>setQuery(e.target.value)}/>}<button className="gt-secondary" onClick={()=>void load()}>Refresh</button></div></div>
      {tab==="Users"&&<div className="gt-table-wrap"><table className="gt-table"><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>{users.map(row=><tr key={row.id}><td>{row.full_name}</td><td>{row.email}</td><td>{row.role}</td><td><span className={row.is_banned?"gt-status":"gt-status active"}>{row.is_banned?"Banned":"Active"}</span></td><td><div className="gt-actions"><button disabled={row.is_banned} onClick={()=>void changeRole(row)}>{row.role==="admin"?"Demote":"Promote"}</button><button className="danger" onClick={()=>void ban(row)}>{row.is_banned?"Unban":"Ban"}</button><button onClick={()=>void revoke(row)}>Revoke sessions</button></div></td></tr>)}</tbody></table></div>}
      {tab==="Activity"&&<div className="gt-table-wrap"><table className="gt-table"><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>IP</th><th>Details</th></tr></thead><tbody>{logs.map(row=><tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.email||"Unknown"}</td><td>{row.action}</td><td>{row.entity_type||"—"} {row.entity_id||""}</td><td>{row.ip_address||"—"}</td><td>{row.details||"—"}</td></tr>)}</tbody></table></div>}
      {tab==="Security"&&<><div className="gt-security-count"><strong>{security.failed_logins_24h}</strong><span>failed or blocked login events in the last 24 hours</span></div><div className="gt-table-wrap"><table className="gt-table"><thead><tr><th>Time</th><th>Email</th><th>Event</th><th>IP</th><th>Browser</th></tr></thead><tbody>{security.events.map(row=><tr key={row.id}><td>{new Date(row.created_at).toLocaleString()}</td><td>{row.email||"Unknown"}</td><td>{row.action}</td><td>{row.ip_address||"—"}</td><td>{row.user_agent||"—"}</td></tr>)}</tbody></table></div></>}</section>
    <section className="gt-panel"><p className="gt-eyebrow">DATA EXPORTS</p><h3>Download reports</h3><div className="gt-export-actions"><button className="gt-secondary" onClick={()=>void exportCsv("/api/admin/export/users","gymtrack-users.csv")}>Users CSV</button><button className="gt-secondary" onClick={()=>void exportCsv("/api/admin/export/members","gymtrack-members.csv")}>Members CSV</button><button className="gt-secondary" onClick={()=>void exportCsv("/api/admin/export/activity","gymtrack-activity.csv")}>Activity CSV</button></div></section>
  </div>;
}

function Profile({user,onUpdate,onLogout}:{user:GymUser;onUpdate:(user:GymUser)=>void;onLogout:()=>void}){
  const [name,setName]=useState(user.full_name),[oldPassword,setOldPassword]=useState(""),[newPassword,setNewPassword]=useState("");
  const [sessions,setSessions]=useState<GymRow[]>([]),[error,setError]=useState(""),[message,setMessage]=useState("");
  const load=useCallback(async()=>{try{setSessions(await api<GymRow[]>("/api/auth/sessions"));}catch(e){setError(e instanceof Error?e.message:"Could not load sessions");}},[]);
  useEffect(()=>{void load();},[load]);
  async function update(event:FormEvent){event.preventDefault();try{const result=await api<GymUser>("/api/me","PATCH",{full_name:name});onUpdate({...user,...result});setMessage("Profile saved.");}catch(e){setError(e instanceof Error?e.message:"Could not update profile");}}
  async function password(event:FormEvent){event.preventDefault();try{await api("/api/me/password","POST",{current_password:oldPassword,new_password:newPassword});setMessage("Password changed. Please sign in again.");setOldPassword("");setNewPassword("");onLogout();}catch(e){setError(e instanceof Error?e.message:"Could not change password");}}
  async function revoke(id:string | number){if(!window.confirm("Revoke this session?"))return;try{await api("/api/auth/sessions/"+id,"DELETE");await load();}catch(e){setError(e instanceof Error?e.message:"Could not revoke session");}}
  return <div className="gt-page-stack"><section className="gt-section-title"><div><p className="gt-eyebrow">ACCOUNT SETTINGS</p><h2>My Profile</h2><p className="gt-muted">Update personal details and manage active sessions.</p></div></section>
    {error&&<div className="gt-alert error">{error}</div>}{message&&<div className="gt-alert success">{message}</div>}
    <div className="gt-two-col"><section className="gt-panel"><h3>Profile details</h3><form onSubmit={update}><label className="gt-field">Full name<input required minLength={2} value={name} onChange={e=>setName(e.target.value)}/></label><label className="gt-field">Email<input disabled value={user.email}/></label><label className="gt-field">Role<input disabled value={user.role}/></label><button className="gt-primary">Save profile</button></form>
      <h3 className="gt-subheading">Change password</h3><form onSubmit={password}><label className="gt-field">Current password<input type="password" required value={oldPassword} onChange={e=>setOldPassword(e.target.value)}/></label><label className="gt-field">New password<input type="password" required minLength={8} value={newPassword} onChange={e=>setNewPassword(e.target.value)}/></label><button className="gt-primary">Change password</button></form></section>
      <section className="gt-panel"><div className="gt-panel-head"><h3>Active sessions</h3><button className="gt-secondary" onClick={()=>void load()}>Refresh</button></div>{sessions.length?sessions.map(row=><div className="gt-session-row" key={row.id}><div><strong>{row.current?"This device":"Other device"}</strong><small>{row.user_agent||"Browser unknown"} · {row.ip_address||"IP unavailable"}</small><small>Last used {new Date(row.last_used_at).toLocaleString()}</small></div><button className="gt-danger-outline" onClick={()=>void revoke(row.id)}>Revoke</button></div>):<p className="gt-empty">No active sessions found.</p>}</section></div>
  </div>;
}

export default function App(){
  const [user,setUser]=useState<GymUser|null>(null),[checking,setChecking]=useState(true),[page,setPage]=useState("Overview"),[apiStatus,setApiStatus]=useState("Checking...");
  const [authError,setAuthError]=useState("");
  const clear=useCallback(()=>{clearAccessToken();setUser(null);setPage("Overview");},[]);
  useEffect(()=>{
    let live=true;
    window.addEventListener("gymtrack:logout",clear);
    (async()=>{try{const restored=await restoreSession();if(live)setUser(restored);}catch{if(live)clear();}finally{if(live)setChecking(false);}})();
    api("/api/health").then(()=>live&&setApiStatus("Connected")).catch(()=>live&&setApiStatus("Offline"));
    return()=>{live=false;window.removeEventListener("gymtrack:logout",clear);};
  },[clear]);
  async function signOut(){try{await logout();}finally{clear();}}
  const navigation=user?.role==="admin"?navAdmin:navUser;
  useEffect(()=>{if(user&&!navigation.includes(page))setPage("Overview");},[user,page,navigation.join("|")]);
  if(checking)return <div className="gt-loading"><div className="gt-spinner"/><p>Restoring GymTrack session…</p></div>;
  if(!user)return <LoginScreen onLogin={setUser}/>;
  const module=modules[page];
  return <div className="layout gt-app">
    <aside className="sidebar"><div className="brand"><span className="brand-icon">GT</span><div><strong>GymTrack</strong><small>Management workspace</small></div></div><p className="nav-label">WORKSPACE</p>
      {navigation.map(item=><button key={item} className={page===item?"nav-link active":"nav-link"} onClick={()=>setPage(item)}>{icons[item]} &nbsp; {item}</button>)}
      <div className="sidebar-footer"><span className="avatar">{initials(user.full_name)}</span><div><strong>{user.full_name}</strong><small>{user.role}</small></div><button className="gt-side-logout" title="Log out" onClick={()=>void signOut()}>↪</button></div>
    </aside>
    <main className="main"><header className="page-header"><div><p className="eyebrow">YOUR GYM, ORGANIZED</p><h1>{page}</h1><p className="subheading">{user.role==="admin"?"Administrator workspace":"Your personal gym workspace"}</p></div><span className={apiStatus==="Connected"?"api-status connected":"api-status"}><span className="status-dot"/> API: {apiStatus}</span></header>
      {authError&&<div className="gt-alert error">{authError}</div>}
      {page==="Overview"&&<Overview user={user}/>}
      {module&&<DataModule name={page} user={user}/>}
      {page==="Groups"&&<GroupsPage/>}
      {page==="Administration"&&user.role==="admin"&&<Administration/>}
      {page==="Profile"&&<Profile user={user} onUpdate={setUser} onLogout={()=>void signOut()}/>}
      <footer>GymTrack · CSE309 · React + TypeScript / FastAPI / PostgreSQL</footer>
    </main>
  </div>;
}
