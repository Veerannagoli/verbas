(() => {
  "use strict";

  const NAV_H = 64;
  const navbar = document.getElementById("navbar");
  const menuBtn = document.getElementById("menuBtn");
  const navLinks = document.getElementById("navLinks");

  window.addEventListener("scroll", () => {
    navbar?.classList.toggle("scrolled", window.scrollY > 15);
  }, { passive: true });

  menuBtn?.addEventListener("click", () => {
    const open = navLinks?.classList.toggle("open") || false;
    menuBtn.setAttribute("aria-expanded", String(open));
  });

  // Smooth scroll to the exact section, accounting for the sticky navbar.
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const id = link.getAttribute("href");
      if (!id || id === "#") return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      const top = id === "#home" ? 0 : target.getBoundingClientRect().top + window.scrollY - NAV_H + 1;
      window.scrollTo({ top, behavior: "smooth" });
      history.replaceState(null, "", id);
      navLinks?.classList.remove("open");
      menuBtn?.setAttribute("aria-expanded", "false");
    });
  });

  // Highlight the nav link for the section currently in view.
  const map = { home: "home", services: "services", growth: "services", "ai-automations": "services",
    approach: "approach", about: "about", blog: "blog", contact: "contact" };
  const navAnchors = [...document.querySelectorAll('.nav-links a[href^="#"]:not(.nav-cta)')];
  const sections = [...document.querySelectorAll("main section[id]")];
  function setActive() {
    const y = window.scrollY + NAV_H + window.innerHeight * 0.3;
    let current = "home";
    sections.forEach((s) => { if (s.offsetTop <= y) current = s.id; });
    const key = map[current] || current;
    navAnchors.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${key}`));
  }
  window.addEventListener("scroll", setActive, { passive: true });
  setActive();

  // Enquiry form
  const form = document.getElementById("enquiryForm");
  const emailBtn = document.getElementById("emailSubmitBtn");
  const whatsappBtn = document.getElementById("whatsappSubmitBtn");
  const status = document.getElementById("success");
  const WHATSAPP_NUMBER = "919951144669";

  const getPayload = () => {
    const d = new FormData(form);
    const f = (k) => String(d.get(k) || "").trim();
    return { name: f("name"), email: f("email"), phone: f("phone"), company: f("company"),
      need: f("need"), budget: f("budget"), timeline: f("timeline"), message: f("message") };
  };
  const showStatus = (msg, type = "") => {
    if (!status) return;
    status.textContent = msg;
    status.className = `success show ${type}`.trim();
  };
  const clearStatus = () => {
    if (!status) return;
    status.textContent = "";
    status.className = "success";
  };
  const whatsappText = (p) => [
    "Hello Verbas,", "", "I would like to make a project enquiry.", "",
    `Name: ${p.name}`, `Email: ${p.email}`, `Phone: ${p.phone || "Not provided"}`,
    `Company: ${p.company || "Not provided"}`, `Service: ${p.need}`,
    `Timeline: ${p.timeline || "Not specified"}`, "", "Project details:", p.message
  ].join("\n");

  whatsappBtn?.addEventListener("click", async () => {
    clearStatus();
    if (!form.reportValidity()) return;
    const p = getPayload();
    const url = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(whatsappText(p))}`;
    try {
      await fetch("/api/whatsapp-enquiry", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p), keepalive: true });
    } catch (_) { /* WhatsApp still opens */ }
    showStatus("WhatsApp is opening with your enquiry ready to send.", "loading");
    window.open(url, "_blank", "noopener,noreferrer");
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();
    if (!form.reportValidity()) return;
    const p = getPayload();
    emailBtn.disabled = whatsappBtn.disabled = true;
    const original = emailBtn.innerHTML;
    emailBtn.textContent = "Sending…";
    showStatus("Sending your enquiry securely…", "loading");
    try {
      const res = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.message || "We could not send your enquiry right now.");
      form.reset();
      showStatus(data.message || "Your enquiry has been sent. We will get back to you soon.");
    } catch (err) {
      showStatus(err.message || "Something went wrong. Please try again.", "error");
    } finally {
      emailBtn.disabled = whatsappBtn.disabled = false;
      emailBtn.innerHTML = original;
    }
  });
})();
