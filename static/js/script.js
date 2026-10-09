(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const menuBtn = $("menuBtn"), nav = $("navLinks");
  menuBtn.addEventListener("click", () => menuBtn.setAttribute("aria-expanded", nav.classList.toggle("open")));
  nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => nav.classList.remove("open")));

  // Sample AI call: one orchestrated moment in the hero
  const lines = [
    ["ai", "Hello, this is Verbas calling for Sharma Traders. Invoice 1042 for ₹18,500 is due today."],
    ["cu", "I'll pay by this evening."],
    ["ai", "Thank you. I'll send the payment link on WhatsApp and call again tomorrow if needed."]
  ];
  const chat = $("chat"), tally = $("tally"), replay = $("replay");
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let timers = [];
  function play() {
    timers.forEach(clearTimeout); timers = [];
    chat.innerHTML = ""; tally.classList.remove("on"); replay.style.display = "none";
    lines.forEach(([who, text], i) => timers.push(setTimeout(() => {
      const m = document.createElement("div"); m.className = "m " + who; m.textContent = text; chat.appendChild(m);
    }, still ? 0 : 900 + i * 1900)));
    timers.push(setTimeout(() => { tally.classList.add("on"); replay.style.display = "inline-flex"; }, still ? 0 : 900 + lines.length * 1900));
  }
  replay.className = "replay btn sm"; play(); replay.addEventListener("click", play);

  document.querySelectorAll("[data-need]").forEach((a) => a.addEventListener("click", () => { $("need").value = a.dataset.need; }));

  const form = $("enquiryForm"), emailBtn = $("emailSubmitBtn"), waBtn = $("whatsappSubmitBtn"), status = $("success");
  const WA = "919951144669";
  const payload = () => { const d = new FormData(form), f = (k) => String(d.get(k) || "").trim();
    return { name: f("name"), email: f("email"), phone: f("phone"), company: f("company"), need: f("need"), timeline: f("timeline"), message: f("message"), website: f("website") }; };
  const show = (msg, type = "") => { status.textContent = msg; status.className = ("success show " + type).trim(); };
  const clear = () => { status.textContent = ""; status.className = "success"; };
  const waText = (p) => ["Hello Verbas,", "", "I would like to make a project enquiry.", "", `Name: ${p.name}`, `Email: ${p.email}`,
    `Phone: ${p.phone || "Not provided"}`, `Company: ${p.company || "Not provided"}`, `Service: ${p.need}`, `Timeline: ${p.timeline || "Not specified"}`, "", "Project details:", p.message].join("\n");

  waBtn.addEventListener("click", async () => {
    clear(); if (!form.reportValidity()) return;
    const p = payload();
    try { await fetch("/api/whatsapp-enquiry", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p), keepalive: true }); } catch (_) {}
    show("Opening WhatsApp with your enquiry ready to send.", "loading");
    window.open(`https://wa.me/${WA}?text=${encodeURIComponent(waText(p))}`, "_blank", "noopener,noreferrer");
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); clear(); if (!form.reportValidity()) return;
    emailBtn.disabled = waBtn.disabled = true; const label = emailBtn.textContent; emailBtn.textContent = "Sending…";
    show("Sending your enquiry…", "loading");
    try {
      const res = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.message || "We could not send your enquiry right now.");
      form.reset(); show(data.message || "Your enquiry has been sent. We will reply soon.");
    } catch (err) { show(err.message || "Something went wrong. Please try again or use WhatsApp.", "error"); }
    finally { emailBtn.disabled = waBtn.disabled = false; emailBtn.textContent = label; }
  });
})();
