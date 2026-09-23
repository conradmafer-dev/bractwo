"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const canvas = $("world"), ctx = canvas.getContext("2d", { alpha: false });
  const mini = $("minimap"), mctx = mini.getContext("2d");
  const ui = Object.fromEntries(Array.from(document.querySelectorAll("[id]"), element => [element.id, element]));
  const classInfo = {
    knight: {name:"Rycerz",icon:"⚔",color:"#f8d377",cape:"#cc4845",ability:"Bastion",weapon:"sword"},
    paladin: {name:"Paladyn",icon:"➶",color:"#f1d99c",cape:"#9e682e",ability:"Mocny strzał",weapon:"bow"},
    mage: {name:"Mag",icon:"✧",color:"#b6c7ff",cape:"#4d65bd",ability:"Krąg ognia",weapon:"staff"},
    druid: {name:"Druid",icon:"❋",color:"#c0e895",cape:"#478e4d",ability:"Odnowa",weapon:"staff"}
  };
  let world = { width:3200,height:2304,spawn:{x:560,y:1180},obstacles:[],zones:[],river:{x:1500,y:0,w:180,h:2304,bridge_y:1080,bridge_h:150},merchant:{x:680,y:1180,name:"Kupiec"},safe_zone:{x:560,y:1180,radius:260},classes:{},pvp_rules:{min_level:8} };
  let snapshot = { players: [], enemies: [], world: {}, time: 0 };
  let myId = null, me = null, socket = null, playing = false, createAccount = false, connecting = false;
  let connectionSerial = 0, loginTimer = null, lastSnapshotAt = 0, ground = null;
  let viewport = { w: innerWidth, h: innerHeight, dpr: 1 }, camera = { x: 660, y: 1080, scale: 1 };
  let visuals = new Map(), particles = [], lastFrame = performance.now(), nextAttackAt = 0;
  const heldKeys = new Set();
  const joystick = { x: 0, y: 0, pointer: null };
  let attackPointer = null, attackHeld = false, blurPaused = false;
  let nearby = null, selectedClass = "knight", selectedTarget = null, pendingInvite = null;
  let inventorySignature = "", playersSignature = "", legacyPrompted = false, lastTargetWarning = 0;
  let panelMode = "inventory", questSignature = "", activeGoal = null;
  let groundChunks=new Map(), expansionTab='spells', expansionSignature='', selectedRune='fire', atlasMode='nearby', navigationGoal=null;
  let effects = new Map(), seenEffects = new Map(), floatingTexts = [];
  const touches = matchMedia("(pointer: coarse)").matches;
  const TAU = Math.PI * 2;
  const Runtime = globalThis.BractwoRuntime, fpsMeter = new Runtime.FrameRateMeter();
  const numberFormat = new Intl.NumberFormat("pl-PL", {maximumFractionDigits:0});
  let surfaceMap = null;
  let selectedEnemy = null, staticIndex = null, staticCandidates = [], staticStamp = "";
  let warmQueue = [], warmScheduled = false, warmStamp = "", chunkLimit = 32, protectedChunks = new Set();
  let minimapSnapshot = null, minimapViewport = "";
  const battleRows = new Map();

  function readRemembered(key) { try { return localStorage.getItem(key) || ""; } catch (_) { return ""; } }
  function remember(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* private browsing */ } }
  const defaultServer = location.protocol === "file:" ? "ws://127.0.0.1:8080/ws" : `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`;
  ui.nameInput.value = readRemembered("bractwo.username");
  // A saved address is useful for the standalone file; a served client follows its own server.
  ui.serverInput.value = location.protocol === "file:" ? readRemembered("bractwo.server") || defaultServer : defaultServer;

  function setMode(create) {
    createAccount = create; ui.classPicker.hidden = !create;
    ui.loginTab.classList.toggle("active", !create); ui.registerTab.classList.toggle("active", create);
    ui.loginTab.setAttribute("aria-selected", String(!create)); ui.registerTab.setAttribute("aria-selected", String(create));
    ui.passwordInput.autocomplete = create ? "new-password" : "current-password";
    ui.connectButton.replaceChildren(document.createTextNode(create ? "Stwórz postać i wyrusz" : "Wejdź do doliny"));
    const arrow = document.createElement("span"); arrow.textContent = "↗"; ui.connectButton.append(arrow);
    ui.authError.textContent = "";
  }
  ui.loginTab.addEventListener("click", () => setMode(false));
  ui.registerTab.addEventListener("click", () => setMode(true));
  for (const button of document.querySelectorAll("#classPicker [data-class]")) button.addEventListener("click", () => {
    selectedClass = button.dataset.class;
    for (const option of ui.classPicker.querySelectorAll("[data-class]")) {
      option.classList.toggle("selected", option.dataset.class === selectedClass);
      option.setAttribute("aria-pressed", String(option.dataset.class === selectedClass));
    }
  });
  for (const original of ui.classPicker.querySelectorAll("[data-class]")) {
    const button = original.cloneNode(true); button.classList.remove("selected"); button.removeAttribute("aria-pressed");
    button.addEventListener("click", () => { resetControls(); send({type:"choose_class",class_id:button.dataset.class}); });
    ui.legacyChoices.append(button);
  }
  if (!ui.nameInput.value) setMode(true);

  function validateServer(raw) {
    let url;
    try { url = new URL(raw.trim()); } catch (_) { throw new Error("Wpisz pełny adres serwera, np. ws://127.0.0.1:8080/ws."); }
    if (!["ws:", "wss:"].includes(url.protocol)) throw new Error("Adres musi zaczynać się od ws:// lub wss://.");
    const host = url.hostname.toLowerCase();
    const octets = host.split(".").map(Number);
    const ipv4 = /^\d{1,3}(\.\d{1,3}){3}$/.test(host) && octets.every((value) => value >= 0 && value <= 255);
    const privateIPv4 = ipv4 && (octets[0] === 127 || octets[0] === 10 || (octets[0] === 192 && octets[1] === 168) || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) || (octets[0] === 169 && octets[1] === 254));
    const local = host === "localhost" || host.endsWith(".localhost") || host === "[::1]" || host.endsWith(".local") || privateIPv4 || /^\[f[cd][0-9a-f]{2}:/.test(host);
    if (url.protocol !== "wss:" && !local) throw new Error("Połączenie z serwerem w internecie wymaga wss://, aby chronić hasło.");
    if (location.protocol === "https:" && url.protocol !== "wss:") throw new Error("Ta strona działa przez HTTPS. Użyj adresu wss://.");
    if (url.username || url.password || url.hash) throw new Error("Adres serwera nie może zawierać danych logowania ani fragmentu #.");
    return url.href;
  }
  function busy(value) { connecting = value; ui.connectButton.disabled = value; ui.loginTab.disabled = value; ui.registerTab.disabled = value; }
  function send(packet) { if (socket && socket.readyState === WebSocket.OPEN) {
      if (selectedEnemy && ['ability','rune_use'].includes(packet.type)) packet = {...packet, enemy_id:selectedEnemy};
      socket.send(JSON.stringify(packet));
    } }
  function notice(text, type = "") {
    if (!text) return;
    const item = document.createElement("div"); item.className = `notice ${type}`; item.textContent = String(text);
    ui.noticeFeed.append(item);
    while (ui.noticeFeed.children.length > (viewport.h < 500 ? 1 : viewport.w < 560 ? 2 : 3)) ui.noticeFeed.firstChild.remove();
    setTimeout(() => { item.classList.add("fade"); setTimeout(() => item.remove(), 1300); }, type === "chat" ? 12000 : 7500);
  }
  ui.authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (connecting) return;
    let address;
    try { address = validateServer(ui.serverInput.value); } catch (error) { ui.authError.textContent = error.message; return; }
    const name = ui.nameInput.value.trim(), password = ui.passwordInput.value;
    if (!name || password.length < 8) { ui.authError.textContent = "Podaj imię i hasło mające co najmniej 8 znaków."; return; }
    const serial = ++connectionSerial;
    if (socket) socket.close();
    resetControls(); busy(true); ui.authError.textContent = "Łączenie z doliną…";
    remember("bractwo.username", name); remember("bractwo.server", address);
    try { socket = new WebSocket(address); } catch (_) { busy(false); ui.authError.textContent = "Nie udało się rozpocząć połączenia. Sprawdź adres serwera."; return; }
    const activeSocket = socket;
    activeSocket.addEventListener("open", () => {
      if (serial !== connectionSerial) return;
      send({ type: "hello", name, password, create: createAccount, class_id:selectedClass, compact_state:true });
      ui.authError.textContent = createAccount ? "Tworzenie postaci…" : "Wczytywanie postaci…";
    });
    activeSocket.addEventListener("message", (event) => {
      if (serial !== connectionSerial) return;
      let packet;
      try { packet = JSON.parse(event.data); } catch (_) { return; }
      if (!packet || typeof packet !== "object") return;
      if (packet.type === "welcome") {
        clearTimeout(loginTimer); busy(false); playing = true; blurPaused = false; myId = String(packet.id);
        world = { ...world, ...(packet.world || {}) };
        world.obstacles = world.obstacles || []; world.zones = world.zones || [];
        selectedTarget = null; selectedEnemy = null; battleRows.clear(); ui.battleEnemies.replaceChildren(); pendingInvite = null; legacyPrompted = false; expansionSignature = ""; navigationGoal = null;
        inventorySignature = ""; playersSignature = ""; ui.sidePanel.hidden = true; ui.helpPanel.hidden = true;
        ui.legacyClassPanel.hidden = true; ui.partyInvite.hidden = true; ui.chatForm.hidden = true; ui.chatInput.blur(); ui.chatInput.value = ""; questSignature = "";
        ui.minimapCard.hidden = viewport.w < 560;
        updateRules();
        snapshot = { players: [], enemies: [], world: {}, time: 0 }; visuals.clear(); particles = []; effects.clear(); seenEffects.clear(); floatingTexts = []; me = null;
        camera.x = world.spawn?.x || 560; camera.y = world.spawn?.y || 1180;
        buildStaticIndex(); buildGround(); fpsMeter.reset(); ui.passwordInput.value = ""; ui.authError.textContent = "";
        ui.authScreen.hidden = true; ui.gameUI.hidden = false; ui.disconnectPanel.hidden = true; ui.deathPanel.hidden = true;
        ui.noticeFeed.replaceChildren(); ui.connectionStatus.innerHTML = "<i></i> ONLINE";
        lastSnapshotAt = performance.now();
        document.activeElement?.blur();
        ui.chatLog.replaceChildren(element("div","chat-hint","Enter — napisz do graczy w dolinie"));
        if (touches) notice("Przesuń lewy joystick. Przytrzymaj Atakuj, by walczyć.");
        send({ type: "input", x: 0, y: 0 });
      } else if (packet.type === "state" && playing) {
        receiveState(packet);
      } else if (packet.type === "error") {
        if (playing) notice(packet.text || "Nie można teraz wykonać tej czynności.", "error");
        else { clearTimeout(loginTimer); ui.authError.textContent = packet.text || "Logowanie nie powiodło się."; busy(false); activeSocket.close(); }
      } else if (packet.type === "party_invite") {
        pendingInvite = packet; ui.inviteText.textContent = `${packet.name || "Gracz"} zaprasza cię do drużyny.`;
        ui.partyInvite.hidden = false;
      } else if (packet.type === "notice") {
        notice(packet.text, "reward");
      } else if (packet.type === "chat") {
        addChat(packet);
      }
    });
    activeSocket.addEventListener("error", () => {
      if (serial === connectionSerial && !playing) ui.authError.textContent = "Brak połączenia. Sprawdź, czy serwer działa i czy adres jest poprawny.";
    });
    activeSocket.addEventListener("close", () => {
      if (serial !== connectionSerial) return;
      clearTimeout(loginTimer); busy(false); resetControls();
      if (playing) { playing = false; ui.disconnectPanel.hidden = false; ui.connectionStatus.textContent = "ROZŁĄCZONO"; }
      else if (!ui.authError.textContent || ui.authError.textContent.includes("…")) ui.authError.textContent = "Połączenie zostało zamknięte. Spróbuj ponownie.";
    });
    clearTimeout(loginTimer);
    loginTimer = setTimeout(() => {
      if (serial === connectionSerial && !playing) { ui.authError.textContent = "Serwer nie odpowiedział. Sprawdź adres i spróbuj ponownie."; busy(false); activeSocket.close(); }
    }, 12000);
  });

  function backToLogin() {
    resetControls(); ++connectionSerial; clearTimeout(loginTimer);
    if (socket) socket.close(); socket = null; playing = false; busy(false); me = null;
    ui.authScreen.hidden = false; ui.gameUI.hidden = true; ui.passwordInput.value = ""; ui.authError.textContent = "";
    setMode(false); ui.passwordInput.focus();
  }
  $("logoutButton").addEventListener("click", backToLogin);
  $("reconnectButton").addEventListener("click", backToLogin);

  function receiveState(packet) {
    lastSnapshotAt = performance.now();
    const previousMe = me;
    snapshot = { ...packet, players: packet.players || [], enemies: packet.enemies || [], world: packet.world || {} };
    const ownIndex = snapshot.players.findIndex(player => String(player.id) === myId);
    if (ownIndex >= 0) snapshot.players[ownIndex] = Runtime.mergeOwner(previousMe, snapshot.players[ownIndex], packet.owner_delta === true);
    me = ownIndex >= 0 ? snapshot.players[ownIndex] : null;
    const present = new Set();
    for (const [kind, entities] of [["p", snapshot.players], ["e", snapshot.enemies]]) {
      for (const entity of entities) {
        const key = `${kind}:${entity.id}`; present.add(key);
        let visual = visuals.get(key);
        if (!visual) { visual = { x: entity.x, y: entity.y, oldHp: entity.hp, oldAttack: entity.attack_until || 0, attackAt: -10000, move: 0, track:new Runtime.MotionTrack() }; visuals.set(key, visual); }
        if (Math.hypot(visual.x - entity.x, visual.y - entity.y) > 450) { visual.x = entity.x; visual.y = entity.y; }
        if (entity.hp < visual.oldHp && entity.hp >= 0) { addParticles(entity.x, entity.y - 16, kind === "p" ? "#ef7868" : "#f4c45f", 8); floatingTexts.push({x:entity.x,y:entity.y-44,text:String(Math.ceil(visual.oldHp-entity.hp)),color:kind==="p"?"#ffbaa1":"#fff3ab",life:1.1}); }
        if (entity.attack_until && entity.attack_until > visual.oldAttack) visual.attackAt = performance.now();
        visual.track.push(entity.x, entity.y, Number(packet.time || 0), entity.floor || 0);
        visual.oldHp = entity.hp; visual.oldAttack = entity.attack_until || 0; visual.entity = entity; visual.kind = kind;
      }
    }
    for (const key of visuals.keys()) if (!present.has(key)) visuals.delete(key);
    if (me && (!previousMe || !sameFloor(me,previousMe) || distance(me,previousMe)>450 || (previousMe.hp <= 0 && me.hp > 0))) { camera.x = me.x; camera.y = me.y; }
    if (selectedTarget && !snapshot.players.some(player => String(player.id) === selectedTarget && player.hp > 0 && sameFloor(me,player))) clearTarget();
    if (selectedEnemy && (!me?.alive || !snapshot.enemies.some(enemy => String(enemy.id) === selectedEnemy && enemy.hp > 0 && sameFloor(me,enemy)))) clearTarget();
    for (const effect of packet.effects || []) {
      if (!seenEffects.has(String(effect.id))) {
        seenEffects.set(String(effect.id), Number(packet.time || 0));
        const duration = Number(effect.duration) || .32;
        const age = Math.max(0, Number(packet.time || 0) - Number(effect.time || 0));
        if (age < duration) effects.set(String(effect.id), {...effect, started:performance.now() - age * 1000});
      }
    }
    for (const [id, time] of seenEffects) if (Number(packet.time || 0) - time > 4) seenEffects.delete(id);
    if(me&&previousMe&&me.level>previousMe.level){for(const m of world.milestones||[])if(m.level>previousMe.level&&m.level<=me.level)notice(`Nowe możliwości: ${m.name}. Sprawdź księgę [K].`,"reward");}
    updateHUD();
  }

  function distance(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
  function ownClass() { return classInfo[me?.class_id] || classInfo.knight; }
  function className(id) { return world.classes?.[id]?.name || classInfo[id]?.name || "Rycerz"; }
  function inSafeZone(player) {return (world.safe_zones||[world.safe_zone]).some(zone=>zone&&sameFloor(player,zone)&&distance(player,zone)<=zone.radius);}
  function merchantNear() { return !!me && me.hp > 0 && sameFloor(me,nearestMerchant()) && distance(me,nearestMerchant()) <= (nearestMerchant().radius || 150); }
  function formatNumber(value) { return numberFormat.format(Number(value)||0); }
  function updateRules() {
    const rules=world.pvp_rules||{}, min=rules.min_level||8;
    ui.pvpHelp.textContent=`Osada i postacie poniżej ${min}. poziomu są chronione. Aby zaatakować gracza, wyłącz blokadę PvP i wybierz go kliknięciem w świecie lub na liście graczy. Biała czaszka oznacza agresora. Trzy nieuzasadnione zabójstwa w 24 godziny dają czerwoną czaszkę na 24 godziny. Walka blokuje wejście do osady i bezpieczne wylogowanie przez 20 sekund.`;
  }
  function updateHUD() {
    if (!me) return;
    const info=ownClass(), safety=me.pvp_safety !== false;
    ui.playerName.textContent=me.name; ui.playerLevel.textContent=`POZ. ${formatNumber(me.level||1)}`;
    ui.classText.textContent=me.profession||className(me.class_id); ui.classText.style.color=info.color;
    ui.healthText.textContent=`${Math.ceil(me.hp)} / ${formatNumber(me.max_hp)}`;
    ui.healthFill.style.width=`${Math.max(0,Math.min(100,me.hp/me.max_hp*100))}%`;
    ui.manaText.textContent=`${Math.floor(me.mana||0)} / ${formatNumber(me.max_mana)}`;
    ui.manaFill.style.width=`${Math.max(0,Math.min(100,(me.mana||0)/(me.max_mana||1)*100))}%`;
    ui.xpFill.style.width=`${Math.max(0,Math.min(100,(me.xp||0)/(me.xp_next||1)*100))}%`;
    ui.xpText.textContent=`${formatNumber(me.xp)} / ${formatNumber(me.xp_next)} PD`;
    ui.playerName.title=`Doświadczenie: ${formatNumber(me.xp)} / ${formatNumber(me.xp_next)}`;
    ui.goldText.textContent=formatNumber(me.gold); ui.goldText.title=`${formatNumber(me.gold)} złota`;
    ui.attackButton.querySelector("span").textContent=info.icon;
    ui.onlineCount.textContent=`${snapshot.players.filter(player=>!player.disconnected).length} online`;
    ui.healthCount.textContent=me.potions?.health_potion||0; ui.manaCount.textContent=me.potions?.mana_potion||0;
    ui.healthPotion.disabled=!(me.potions?.health_potion>0) || me.hp<=0;
    ui.manaPotion.disabled=!(me.potions?.mana_potion>0) || me.hp<=0;
    const cooldown=Math.max(0,Number(me.ability_cooldown)||0);
    ui.abilityName.textContent=me.ability_name || world.classes?.[me.class_id]?.ability_name || info.ability;
    ui.abilityIcon.textContent=info.icon; ui.abilityIcon.style.color=info.color;
    ui.abilityCooldown.textContent=cooldown>0?`${Math.ceil(cooldown)}s`:"";
    ui.abilityButton.classList.toggle("cooldown",cooldown>0); ui.abilityButton.disabled=cooldown>0 || me.hp<=0;
    const zone=[...world.zones,...(world.regions||[])].find(item=>sameFloor(me,item)&&me.x>=item.x&&me.x<=item.x+item.w&&me.y>=item.y&&me.y<=item.y+item.h);
    ui.movementStatus.textContent=`${world.surfaces?.[me.surface]?.name||'Trawa'} · ${Number(me.speed||100).toFixed(0)}${me.premium_demo?' · Premium test':''}${me.wind_remaining>0?' · Wiatr +15%':''}${me.ward_remaining>0?' · Osłona PvE':''}`;
    ui.regionName.textContent=(zone?.name||"Dzikie Pogranicze")+(me.floor?` · piętro ${me.floor>0?'+':''}${me.floor}`:"");
    const safe=inSafeZone(me), protectedLevel=me.level<(world.pvp_rules?.min_level||8);
    ui.zoneStatus.textContent=safe?"Bezpieczna osada":protectedLevel?`Ochrona PvP do ${world.pvp_rules?.min_level||8}. poziomu`:"Teren otwarty · PvP z karami";
    const combat=Math.max(0,Number(me.combat_remaining)||0);
    ui.combatStatus.hidden=combat<=0;
    ui.combatStatus.textContent=me.pvp_combat_remaining>0?`PvP: ${Math.ceil(me.pvp_combat_remaining)} s · wejście do osady zablokowane`:`Walka: ${Math.ceil(combat)} s · poczekaj z handlem i wylogowaniem`;
    ui.safetyButton.classList.toggle("danger",!safety); ui.safetyButton.setAttribute("aria-pressed",String(safety));
    ui.safetyButton.textContent=safety?"PvP: blokada ataku":"PvP: ataki włączone";
    ui.safetyButton.title=safety?"Wyłącz blokadę własnych ataków PvP":"Włącz blokadę własnych ataków PvP";
    ui.skullStatus.hidden=!me.skull || me.skull==="none";
    ui.skullStatus.textContent=me.skull==="red"?`☠ Czerwona czaszka · ${me.unjust_kills||0} nieuzasadnionych zabójstw`: `☠ Biała czaszka · ${Math.ceil(me.skull_remaining||0)} s`;
    ui.skullStatus.style.color=me.skull==="red"?"#f39f8a":"#edeadd";
    const target=selectedEnemy?snapshot.enemies.find(enemy=>String(enemy.id)===selectedEnemy):snapshot.players.find(player=>String(player.id)===selectedTarget);
    ui.targetCard.hidden=!target; ui.targetName.textContent=target?.name||"";
    ui.attackButton.classList.toggle("pvp-target",!!selectedTarget); ui.attackLabel.textContent=selectedEnemy?"Atakuj cel":target?(safety?"PvP blokada":"Atak PvP"):"Atakuj";
    nearby=nearestStair() || nearestSite() || nearestNpc() || (merchantNear()?nearestMerchant():null); ui.interactPrompt.hidden=!nearby || !ui.sidePanel.hidden;
    ui.interactButton.classList.toggle("available",!!nearby);
    ui.interactName.textContent=nearby?.name||"Mieszkańcy Przystani";
    ui.interactPrompt.querySelector("small").textContent=nearby?.to_floor!==undefined?"SCHODY · E":nearby?.action?"UŻYJ · E":nearby?.service?"USŁUGI MIEJSKIE":nearby?.id?"ROZMOWA I ZLECENIA":"HANDEL I ODPOCZYNEK";
    ui.deathPanel.hidden=me.hp>0;
    if(me.hp<=0){resetControls();ui.deathText.textContent=`Powrót do osady${me.respawn_in?` za ${Math.ceil(me.respawn_in)} s`:"…"}`;}
    ui.chooseClassButton.hidden=me.class_chosen!==false;
    if(me.class_chosen===false&&!legacyPrompted&&safe){legacyPrompted=true;resetControls();ui.legacyClassPanel.hidden=false;}
    if(me.class_chosen!==false)ui.legacyClassPanel.hidden=true;
    for(const button of ui.legacyChoices.querySelectorAll("button"))button.disabled=!safe||me.hp<=0;
    if(pendingInvite && me.party_id){pendingInvite=null;ui.partyInvite.hidden=true;}
    for(const [id,key]of [['healSpell','mend'],['hasteSpell','haste'],['advancedSpell',spellByLevel(30)],['masterSpell',spellByLevel(80)]]){const spec=world.spells?.[key];ui[id].disabled=!spec||!spellAvailable(spec)||me.mana<spec.mana||me.spell_cooldowns?.[key]>0||me.hp<=0;}
    ui.runeSpell.disabled=!(me.runes?.[selectedRune]>0)||me.rune_cooldown>0||me.hp<=0;
    ui.runeSpell.title=`${world.runes?.[selectedRune]?.name||'Runa'} · ${me.runes?.[selectedRune]||0} [7]`;
    ui.healthCount.textContent=Object.entries(me.potions||{}).filter(([k])=>k.startsWith('health')).reduce((n,[,v])=>n+v,0);
    ui.manaCount.textContent=Object.entries(me.potions||{}).filter(([k])=>k.startsWith('mana')).reduce((n,[,v])=>n+v,0);
    ui.healthPotion.disabled=Number(ui.healthCount.textContent)<1||me.hp<=0;ui.manaPotion.disabled=Number(ui.manaCount.textContent)<1||me.hp<=0;
    updateQuestTracker(); updateBattleList();
    if(!ui.sidePanel.hidden){if(panelMode==="inventory")renderInventory();else if(panelMode==="journal")renderJournal();else if(panelMode==="progression")renderExpansion();else renderPlayers();}
  }
  function nearestNpc(){
    if(!me||me.hp<=0)return null;
    const npc=(world.npcs||[]).filter(n=>sameFloor(me,n)&&distance(me,n)<=(n.radius||150)).sort((a,b)=>distance(me,a)-distance(me,b))[0];
    // At the merchant's counter, E still opens trade; elsewhere the closest resident speaks.
    if(npc&&merchantNear()&&distance(me,nearestMerchant())<distance(me,npc))return null;
    return npc||null;
  }
  function directionTo(point){
    if(!point||!me)return "";
    if(!sameFloor(me,point))return `Piętro ${point.floor||0} · szukaj schodów`;
    const d=distance(me,point),angle=Math.atan2(point.y-me.y,point.x-me.x);
    const arrow=["→","↘","↓","↙","←","↖","↑","↗"][(Math.round(angle/(Math.PI/4))+8)%8];
    return d<65?"Tuż obok":`${arrow} ${Math.max(1,Math.round(d/32))} pól`;
  }
  function questGoal(quest){
    if(!quest)return null;
    const npc=(world.npcs||[]).find(n=>n.id===quest.npc_id);
    if(quest.status!=="active")return npc?{...npc,label:npc.name}:null;
    const objective=(quest.objectives||[]).find(o=>o.count<o.required);
    if(!objective)return npc?{...npc,label:npc.name}:null;
    if(objective.type==="discover"){
      const site=(world.landmarks||[]).find(n=>n.id===objective.target);return site?{...site,label:site.name}:null;
    }
    const enemies=snapshot.enemies.filter(e=>e.kind===objective.target).sort((a,b)=>Number(a.hp<=0)-Number(b.hp<=0)||distance(a,me)-distance(b,me));
    return enemies[0]?{...enemies[0],label:`${objective.label}${enemies[0].hp<=0?" · odradza się":""}`}:(objective.x!==undefined?{...objective,label:objective.label}:npc?{...npc,label:npc.name}:null);
  }
  function updateQuestTracker(){
    if(!me)return;
    if(navigationGoal){activeGoal=navigationGoal;ui.questTrackerTitle.textContent=navigationGoal.label;ui.questTrackerProgress.textContent='Cel nawigacji · usuń w Atlasie [K]';ui.questTrackerDirection.textContent=directionTo(navigationGoal);return;}
    const quests=me.quests||[];
    const quest=quests.find(q=>q.status==="ready")||quests.find(q=>q.status==="active")||quests.find(q=>q.status==="available");
    activeGoal=questGoal(quest);
    ui.questTracker.classList.toggle("ready",quest?.status==="ready");
    if(quest){
      ui.questTrackerTitle.textContent=quest.title;
      ui.questTrackerProgress.textContent=quest.status==="ready"?"Zlecenie wykonane! Wróć po nagrodę.":quest.status==="available"?"Porozmawiaj ze zleceniodawcą [E].":(quest.objectives||[]).map(o=>`${o.count>=o.required?"✓ ":""}${o.label}: ${o.count}/${o.required}`).join(" · ");
      ui.questTrackerDirection.textContent=activeGoal?`${directionTo(activeGoal)} · ${activeGoal.label}`:"Dziennik pokaże szczegóły wyprawy.";
    }else{
      const undiscovered=(world.landmarks||[]).find(l=>!(me.discoveries||[]).includes(l.id));
      activeGoal=undiscovered?{...undiscovered,label:undiscovered.name}:null;
      ui.questTrackerTitle.textContent=undiscovered?"Nieznane ścieżki":"Pogranicze jest twoje";
      ui.questTrackerProgress.textContent=undiscovered?"Wyrusz do kolejnego miejsca z atlasu.":"Zbierz drużynę, poluj na bossów i szukaj rzadkiego wyposażenia.";
      ui.questTrackerDirection.textContent=activeGoal?`${directionTo(activeGoal)} · ${activeGoal.label}`:`Odkrycia ${(me.discoveries||[]).length}/${(world.landmarks||[]).length} · Poziomy bez limitu`;
    }
  }
  function rewardDescription(reward){
    const parts=[];if(reward.xp)parts.push(`${reward.xp} PD`);if(reward.gold)parts.push(`${reward.gold} złota`);
    if(reward.item){const template=reward.item.startsWith("class_weapon_")?`${me?.class_id||"knight"}_weapon_${reward.item.split("_").pop()}`:reward.item;parts.push(world.items?.[template]?.name||"wyposażenie twojej klasy");}
    for(const [key,label]of[["health_potion","mikst. zdrowia"],["mana_potion","mikst. many"]]){const count=reward.potions?.[key]||reward[key];if(count)parts.push(`${count} × ${label}`);}
    return parts.join(" · ");
  }
  function renderJournal(){
    if(!me)return;
    const quests=me.quests||[];
    const signature=JSON.stringify([quests,me.discoveries,me.hp>0,(world.npcs||[]).map(n=>[n.id,Math.round(distance(me,n)/32),distance(me,n)<=(n.radius||150)])]);
    if(signature===questSignature)return;questSignature=signature;
    ui.questList.replaceChildren();
    if(!quests.length)ui.questList.append(element("p","empty-message","Mieszkańcy Przystani czekają na twoją pomoc. Podejdź do strażniczki i naciśnij E."));
    const statuses={available:"Nowe zlecenie",active:"W trakcie",ready:"Odbierz nagrodę",claimed:"Ukończone",locked:"Kolejna wyprawa"};
    for(const quest of quests){
      const row=element("article",`quest-entry ${quest.status}`);row.dataset.questId=quest.id;row.dataset.npcId=quest.npc_id;
      const head=element("div","quest-title");head.append(element("strong","",quest.title),element("span","quest-status",statuses[quest.status]||quest.status));
      row.append(head,element("p","quest-description",quest.description));
      for(const objective of quest.objectives||[]){const progress=element("div",`quest-objective${objective.count>=objective.required?" complete":""}`);progress.append(element("span","",`${objective.count>=objective.required?"✓ ":""}${objective.label}`),element("b","",`${objective.count}/${objective.required}`));row.append(progress);}
      row.append(element("div","quest-reward",`Nagroda: ${rewardDescription(quest.reward||{})}`));
      const npc=(world.npcs||[]).find(n=>n.id===quest.npc_id),close=npc&&sameFloor(me,npc)&&distance(me,npc)<=(npc.radius||150)&&me.hp>0;
      if(npc)row.append(element("div","quest-location",`${npc.name} · ${directionTo(npc)}${close?" · możesz porozmawiać":" · wróć do zleceniodawcy"}`));
      if(quest.status==="available"||quest.status==="ready"){
        const accept=quest.status==="available",button=actionButton(accept?"Przyjmij zlecenie":"Odbierz nagrodę",()=>send({type:accept?"quest_accept":"quest_claim",quest_id:quest.id}),!close);
        button.dataset[accept?"questAccept":"questClaim"]=quest.id;button.title=close?"":`Podejdź do ${npc?.name||"zleceniodawcy"}`;row.append(button);
      }else if(quest.status==="locked"){
        const requirements=Array.isArray(quest.requires)?quest.requires:[quest.requires];
        const names=requirements.filter(Boolean).map(id=>quests.find(q=>q.id===id)?.title||id);
        if(quest.min_level>me.level)row.append(element("div","quest-location",`Wymagany poziom ${quest.min_level}`));
        if(names.length)row.append(element("div","quest-location",`Najpierw ukończ: ${names.join(", ")}`));
      }
      ui.questList.append(row);
    }
    ui.discoveryList.replaceChildren();ui.discoveryCount.textContent=`${(me.discoveries||[]).length}/${(world.landmarks||[]).length}`;
    for(const landmark of world.landmarks||[]){
      const found=(me.discoveries||[]).includes(landmark.id),row=element("div",`discovery-entry${found?"":" unknown"}`);row.dataset.landmarkId=landmark.id;
      row.append(element("strong","",`${found?"✓":"◇"} ${landmark.name}`),element("p","",found?landmark.description:"Nieodkryte miejsce. Dotrzyj tutaj, aby poznać historię i otrzymać nagrodę."),element("small","",directionTo(landmark)));ui.discoveryList.append(row);
    }
  }
  function updateBattleList(){
    const enemies=snapshot.enemies.filter(e=>e.hp>0&&e.alive!==false&&sameFloor(me,e)&&(distance(me,e)<500||String(e.id)===selectedEnemy)).sort((a,b)=>Number(String(b.id)===selectedEnemy)-Number(String(a.id)===selectedEnemy)||distance(me,a)-distance(me,b)).slice(0,5);
    ui.battleList.hidden=!enemies.length||!ui.sidePanel.hidden;
    const present=new Set(enemies.map(e=>String(e.id)));
    for(const [id,row] of battleRows)if(!present.has(id)){row.node.remove();battleRows.delete(id);}
    enemies.forEach((enemy,index)=>{
      const id=String(enemy.id);let row=battleRows.get(id);
      if(!row){
        const node=element('button','battle-row'),text=element('div','battle-enemy'),name=element('span'),distanceText=element('small');node.type='button';node.dataset.enemyId=id;
        text.append(name,distanceText);const hp=element('div','battle-hp'),fill=element('div');hp.append(fill);node.append(text,hp);
        node.addEventListener('pointerdown',event=>{event.preventDefault();selectEnemy(id);});
        node.addEventListener('click',()=>selectEnemy(id));row={node,name,distanceText,fill};battleRows.set(id,row);
      }
      if(row.name.textContent!==enemy.name)row.name.textContent=enemy.name;
      const dist=`${Math.ceil(distance(me,enemy)/32)} pól`;if(row.distanceText.textContent!==dist)row.distanceText.textContent=dist;
      row.fill.style.width=`${Math.max(0,enemy.hp/enemy.max_hp*100)}%`;
      row.node.classList.toggle('targeted',id===selectedEnemy);row.node.setAttribute('aria-pressed',String(id===selectedEnemy));
      if(ui.battleEnemies.children[index]!==row.node)ui.battleEnemies.insertBefore(row.node,ui.battleEnemies.children[index]||null);
    });
  }
  function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
  function actionButton(text,handler,disabled=false,className=""){const button=element("button",className,text);button.type="button";button.disabled=disabled;button.addEventListener("click",handler);return button;}
  function slotName(slot){return {weapon:"Broń",armor:"Pancerz",ring:"Pierścień"}[slot]||slot;}
  function itemStats(item){const parts=[];if(item.attack)parts.push(`Atak +${item.attack}`);if(item.armor)parts.push(`Pancerz +${item.armor}`);return parts.join(" · ")||"Bez premii do statystyk";}
  function renderInventory(){
    if(!me)return;
    const inv=me.inventory||[], equipment=me.equipment||{}, near=merchantNear(), trading=near&&!(me.combat_remaining>0);
    const signature=JSON.stringify([inv,equipment,me.level,me.class_id,me.attack,me.armor,me.speed,me.gold,near,trading,me.hp>0]);
    if(signature===inventorySignature)return;inventorySignature=signature;
    ui.combatStats.textContent=`Atak ${formatNumber(me.attack)} · Pancerz ${formatNumber(me.armor)} · Ruch ${Number(me.speed||100).toFixed(1)}`;
    ui.inventoryCount.textContent=`${inv.length} / 40`;
    ui.equipmentSlots.replaceChildren();
    for(const slot of ["weapon","armor","ring"]){
      const uid=equipment[slot], item=inv.find(entry=>String(entry.uid)===String(uid)), row=element("div","equipment-slot");
      row.dataset.slot=slot;row.append(element("span","item-icon",{weapon:ownClass().icon,armor:"♜",ring:"◉"}[slot]));
      const copy=element("div","item-copy");copy.append(element("span","slot-name",slotName(slot)),element("strong","",item?.name||"Pusty slot"));row.append(copy);
      if(item){const button=actionButton("Zdejmij",()=>send({type:"unequip",slot}),me.hp<=0);button.dataset.unequip=slot;button.dataset.action="unequip";button.dataset.slot=slot;row.append(button);}ui.equipmentSlots.append(row);
    }
    ui.inventoryList.replaceChildren();
    if(!inv.length)ui.inventoryList.append(element("p","empty-message","Pokonuj potwory, aby zdobywać wyposażenie. Każdy łup trafia do twojego plecaka."));
    for(const item of inv){
      const row=element("div",`inventory-item ${["uncommon","rare","epic","legendary"].includes(item.rarity)?item.rarity:""}`);row.dataset.uid=item.uid;
      const head=element("div","item-heading");head.append(element("strong","",item.name||item.template),element("span","",`${formatNumber(item.value)} zł`));
      const validClass=!item.class_ids?.length||item.class_ids.includes(me.class_id), validLevel=me.level>=(item.min_level||1);
      row.append(head,element("div","item-stats",`${world.rarities?.[item.rarity]||item.rarity} · ${item.description||itemStats(item)}${item.description&&item.slot!=="trophy"?" · "+itemStats(item):""}`));
      const restrictions=[`Poz. ${item.min_level||1}`,slotName(item.slot)];
      if(item.class_ids?.length)restrictions.push(item.class_ids.map(className).join(", "));
      row.append(element("div",validClass&&validLevel?"item-stats":"item-requirement",restrictions.join(" · ")));
      const actions=element("div","item-actions"),equipped=String(equipment[item.slot])===String(item.uid);
      if(equipped)actions.append(element("span","equipped-tag","✓ Założone"));
      else if(item.slot!=="trophy"){const equip=actionButton("Załóż",()=>send({type:"equip",uid:item.uid}),!validClass||!validLevel||me.hp<=0);equip.dataset.equip=item.uid;equip.dataset.action="equip";equip.dataset.uid=item.uid;actions.append(equip);}
      const sell=actionButton("Sprzedaj",()=>send({type:"sell",uid:item.uid}),!trading||equipped);sell.dataset.sell=item.uid;sell.dataset.action="sell";sell.dataset.uid=item.uid;sell.title=equipped?"Najpierw zdejmij przedmiot":near?"Sprzedaj kupcowi":"Sprzedaż przy kupcu w osadzie";actions.append(sell);row.append(actions);ui.inventoryList.append(row);
    }
    const prices=world.merchant.prices||world.potion_prices||{};
    for(const [key,id]of[["health_potion","healthPrice"],["mana_potion","manaPrice"]]){const amount=prices[key];ui[id].textContent=typeof amount==="number"?`${amount} zł`:"Cena podana przez kupca";}
    ui.merchantHint.textContent=near&&!trading?"Trwa walka. Poczekaj na wygaśnięcie blokady, aby handlować.":near?"Jesteś przy kupcu. Kupuj mikstury i sprzedawaj niezałożony sprzęt.":"Podejdź do kupca w osadzie, aby handlować.";
    ui.buyHealth.disabled=!trading||Number(me.gold)<Number(prices.health_potion??Infinity);ui.buyMana.disabled=!trading||Number(me.gold)<Number(prices.mana_potion??Infinity);ui.restButton.disabled=!trading;
  }
  function renderPlayers(){
    if(!me)return;
    const others=snapshot.players.filter(player=>String(player.id)!==myId);
    const signature=JSON.stringify([others.map(p=>[p.id,p.name,p.level,p.class_id,p.party_id,p.skull,p.disconnected]),me.party_id,me.party_members,selectedTarget]);
    if(signature===playersSignature)return;playersSignature=signature;
    const members=snapshot.players.filter(player=>(me.party_members||[]).map(String).includes(String(player.id)));
    ui.partySummary.textContent=me.party_id?`Drużyna ${members.length||me.party_members?.length||1}/4: ${members.map(p=>p.name).join(", ")}`:"Podróżujesz samotnie. Zaproś innych graczy.";
    ui.leaveParty.hidden=!me.party_id;ui.playersList.replaceChildren();
    if(!others.length)ui.playersList.append(element("p","empty-message","Nie ma jeszcze innych graczy. Możesz polować i rozwijać postać samodzielnie."));
    for(const player of others){
      const row=element("div",`player-row${selectedTarget===String(player.id)?" targeted":""}`);row.dataset.playerId=player.id;
      const head=element("div","player-heading"), name=element("strong","",`${player.skull&&player.skull!=="none"?"☠ ":""}${player.name}`);if(player.skull==="red")name.style.color="#efa58e";
      head.append(name,element("small","",`Poz. ${formatNumber(player.level)}`));row.append(head,element("div","player-detail",`${className(player.class_id)}${player.disconnected?" · rozłączony w walce":""}${me.party_id&&player.party_id===me.party_id?" · twoja drużyna":""}`));
      const actions=element("div","player-buttons"), leader=!me.party_id||String(me.party_id)===myId;
      const invite=actionButton("Zaproś",()=>send({type:"party_invite",target_id:player.id}),!leader||!!player.party_id||player.disconnected||me.party_members?.length>=4);invite.dataset.invite=player.id;invite.dataset.action="invite";invite.dataset.playerId=player.id;
      const target=actionButton("Cel PvP",()=>selectTarget(String(player.id)),false,"target-button");target.dataset.target=player.id;target.dataset.action="target";target.dataset.playerId=player.id;actions.append(invite,target);row.append(actions);ui.playersList.append(row);
    }
  }
  function setPanel(mode){resetControls();panelMode=mode;ui.sidePanel.hidden=false;ui.inventoryView.hidden=mode!=="inventory";ui.playersView.hidden=mode!=="players";ui.journalView.hidden=mode!=="journal";ui.progressionView.hidden=mode!=="progression";ui.progressionTab.classList.toggle("active",mode==="progression");ui.journalTab.classList.toggle("active",mode==="journal");ui.inventoryTab.classList.toggle("active",mode==="inventory");ui.playersTab.classList.toggle("active",mode==="players");ui.minimapCard.hidden=true;updateHUD();}
  function togglePanel(mode){if(!ui.sidePanel.hidden&&panelMode===mode){ui.sidePanel.hidden=true;updateHUD();}else setPanel(mode);}
  function selectTarget(id){resetControls();selectedEnemy=null;selectedTarget=id;playersSignature="";ui.sidePanel.hidden=true;updateHUD();notice("Wybrano cel PvP. Atak wymaga wyłączonej blokady PvP.");}
  function selectEnemy(id){
    const enemy=snapshot.enemies.find(e=>String(e.id)===id&&e.hp>0&&sameFloor(me,e));if(!enemy)return;
    selectedEnemy=id;selectedTarget=null;playersSignature="";ui.sidePanel.hidden=true;updateHUD();
  }
  function clearTarget(){resetControls();selectedTarget=null;selectedEnemy=null;playersSignature="";if(me)updateHUD();}
  function typing() { return ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName); }
  function canControl() { return playing && me && me.hp > 0 && !document.hidden && !blurPaused && ui.helpPanel.hidden && ui.disconnectPanel.hidden && ui.legacyClassPanel.hidden && ui.sidePanel.hidden && !typing(); }
  function resetControls() {
    heldKeys.clear(); joystick.x = 0; joystick.y = 0; joystick.pointer = null; attackPointer = null; attackHeld = false;
    ui.joystickKnob.style.transform = ""; ui.attackButton.classList.remove("held");
    if (playing) send({ type: "input", x: 0, y: 0 });
  }
  function interact(){if(!canControl())return;const stair=nearestStair();if(stair){send({type:'descend'});return;}if(nearestSite()){send({type:'interact'});return;}const npc=nearestNpc();if(npc?.service){openExpansion(npc.service==='master'?'growth':'services');return;}if(npc){setPanel('journal');const quest=Array.from(ui.questList.children).find(row=>row.dataset.npcId===npc.id);quest?.scrollIntoView({block:'nearest'});}else if(merchantNear()){send({type:'interact'});setPanel('inventory');}else openExpansion('atlas');}
  function ability(){if(canControl())send({type:"ability"});}
  function potion(item){if(playing&&me?.hp>0)send({type:"potion",item});}
  function toggleHelp(){resetControls();ui.helpPanel.hidden=!ui.helpPanel.hidden;}
  function openChat(){
    if(!playing)return; resetControls(); ui.chatForm.hidden=false;
    ui.chatForm.parentElement.classList.add("writing"); ui.chatInput.focus({preventScroll:true});
  }
  function closeChat(){ui.chatInput.blur();ui.chatForm.hidden=true;ui.chatForm.parentElement.classList.remove("writing");resetControls();}
  function submitChat(){const text=ui.chatInput.value.trim();if(playing&&text)send({type:"chat",text});ui.chatInput.value="";closeChat();}
  function addChat(packet){
    ui.chatLog.querySelector(".chat-hint")?.remove();
    const row=element("div","chat-line"), name=element("b","",`${packet.name||"Wędrowiec"}: `);
    row.append(name,document.createTextNode(packet.text||""));ui.chatLog.append(row);
    while(ui.chatLog.children.length>60)ui.chatLog.firstChild.remove();ui.chatLog.scrollTop=ui.chatLog.scrollHeight;
  }
  ui.progressionButton.addEventListener('click',()=>togglePanel('progression'));ui.progressionTab.addEventListener('click',()=>setPanel('progression'));
  ui.atlasButton.addEventListener('click',()=>openExpansion('atlas'));ui.bookSpell.addEventListener('click',()=>openExpansion('spells'));
  ui.progressionNav.addEventListener('click',event=>{if(event.target.dataset.view){expansionTab=event.target.dataset.view;expansionSignature='';renderExpansion();}});
  ui.healSpell.addEventListener('click',()=>cast('mend'));ui.hasteSpell.addEventListener('click',()=>cast('haste'));ui.advancedSpell.addEventListener('click',()=>cast(spellByLevel(30)));ui.masterSpell.addEventListener('click',()=>cast(spellByLevel(80)));ui.runeSpell.addEventListener('click',()=>send({type:'rune_use',rune_id:selectedRune}));
  ui.helpButton.addEventListener("click",toggleHelp);ui.closeHelp.addEventListener("click",toggleHelp);
  ui.mapButton.addEventListener("click",()=>{ui.minimapCard.hidden=!ui.minimapCard.hidden;ui.sidePanel.hidden=true;});
  ui.inventoryButton.addEventListener("click",()=>togglePanel("inventory"));ui.partyButton.addEventListener("click",()=>togglePanel("players"));
  ui.journalButton.addEventListener("click",()=>togglePanel("journal"));ui.questTracker.addEventListener("click",()=>setPanel("journal"));ui.journalTab.addEventListener("click",()=>setPanel("journal"));
  ui.inventoryTab.addEventListener("click",()=>setPanel("inventory"));ui.playersTab.addEventListener("click",()=>setPanel("players"));
  ui.closePanel.addEventListener("click",()=>{ui.sidePanel.hidden=true;updateHUD();});
  ui.interactButton.addEventListener("click",interact);ui.abilityButton.addEventListener("click",ability);
  ui.healthPotion.addEventListener("click",()=>useBestPotion("health_potion"));ui.manaPotion.addEventListener("click",()=>useBestPotion("mana_potion"));
  ui.buyHealth.addEventListener("click",()=>send({type:"buy",item:"health_potion"}));ui.buyMana.addEventListener("click",()=>send({type:"buy",item:"mana_potion"}));
  ui.restButton.addEventListener("click",()=>send({type:"interact"}));
  ui.safetyButton.addEventListener("click",()=>{if(!playing||!me)return;resetControls();send({type:"pvp_safety",enabled:me.pvp_safety===false});});
  ui.clearTarget.addEventListener("click",clearTarget);
  ui.leaveParty.addEventListener("click",()=>send({type:"party_leave"}));
  ui.acceptInvite.addEventListener("click",()=>{if(pendingInvite)send({type:"party_accept",leader_id:pendingInvite.leader_id});pendingInvite=null;ui.partyInvite.hidden=true;});
  ui.declineInvite.addEventListener("click",()=>{pendingInvite=null;ui.partyInvite.hidden=true;});
  ui.chooseClassButton.addEventListener("click",()=>{resetControls();ui.legacyClassPanel.hidden=false;});ui.closeLegacy.addEventListener("click",()=>{ui.legacyClassPanel.hidden=true;});
  ui.chatButton.addEventListener("click",()=>{if(ui.chatForm.hidden)openChat();else closeChat();});
  ui.chatForm.addEventListener("submit",event=>{event.preventDefault();submitChat();});
  canvas.addEventListener("pointerdown",event=>{
    if(!canControl())return;
    const x=(event.clientX-viewport.w/2)/camera.scale+camera.x,y=(event.clientY-viewport.h/2)/camera.scale+camera.y;
    const nearest=Runtime.hitActor(visuals.values(),x,y,myId,me.floor||0,camera.scale);
    if(nearest){if(nearest.kind==='e')selectEnemy(String(nearest.entity.id));else selectTarget(String(nearest.entity.id));}
    else {
      const npc=(world.npcs||[]).find(n=>sameFloor(me,n)&&Math.hypot(n.x-x,n.y-20-y)<36);
      if(npc?.service){openExpansion(npc.service==="master"?"growth":"services");}else if(npc){setPanel("journal");const row=Array.from(ui.questList.children).find(q=>q.dataset.npcId===npc.id);row?.scrollIntoView({block:"nearest"});}
    }
  });
  // Capture Enter before a focused HUD button can consume it or submit another form.
  addEventListener("keydown",event=>{
    if(!playing)return;
    if(event.code==="Enter" && !event.isComposing){
      event.preventDefault();event.stopPropagation();
      if(!event.repeat){if(document.activeElement===ui.chatInput)submitChat();else openChat();}return;
    }
    if(typing()){
      if(event.code==="Escape"){event.preventDefault();closeChat();}
      return;
    }
    if(["Space","ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].includes(event.code))event.preventDefault();
    if(event.code==="Escape"){event.preventDefault();clearTarget();ui.helpPanel.hidden=true;ui.legacyClassPanel.hidden=true;ui.sidePanel.hidden=true;closeChat();return;}
    if(!event.repeat){
      if(event.code==="KeyH"){toggleHelp();return;}
      if(event.code==="KeyM"){ui.mapButton.click();return;}
      if(event.code==="KeyI"){togglePanel("inventory");return;}
      if(event.code==="KeyP"){togglePanel("players");return;}
      if(event.code==="KeyK"){togglePanel("progression");return;}
      if(event.code==="KeyJ"){togglePanel("journal");return;}
    }
    if(!canControl())return;heldKeys.add(event.code);
    if(!event.repeat){if(event.code==="KeyE")interact();if(event.code==="KeyF")ability();if(event.code==="Digit1")useBestPotion("health_potion");if(event.code==="Digit2")useBestPotion("mana_potion");if(event.code==="Digit3")cast("mend");if(event.code==="Digit4")cast("haste");if(event.code==="Digit5")cast(spellByLevel(30));if(event.code==="Digit6")cast(spellByLevel(80));if(event.code==="Digit7")send({type:"rune_use",rune_id:selectedRune});}
  },true);
  addEventListener("keyup", (event) => { heldKeys.delete(event.code); });
  addEventListener("blur", () => { resetControls(); blurPaused = true; });
  addEventListener("focus", () => { blurPaused = false; });
  document.addEventListener("visibilitychange", () => { resetControls(); if (!document.hidden) blurPaused = false; });
  ui.joystick.addEventListener("pointerdown", (event) => {
    if (!canControl() || joystick.pointer !== null) return;
    event.preventDefault(); joystick.pointer = event.pointerId; ui.joystick.setPointerCapture(event.pointerId); updateJoystick(event);
  });
  function updateJoystick(event) {
    if (event.pointerId !== joystick.pointer) return;
    const rect = ui.joystick.getBoundingClientRect(); const radius = rect.width * .34;
    let x = event.clientX - rect.left - rect.width / 2, y = event.clientY - rect.top - rect.height / 2;
    const length = Math.hypot(x, y); if (length > radius) { x *= radius / length; y *= radius / length; }
    joystick.x = x / radius; joystick.y = y / radius;
    if (length < 7) { joystick.x = 0; joystick.y = 0; }
    ui.joystickKnob.style.transform = `translate(${x}px, ${y}px)`;
  }
  ui.joystick.addEventListener("pointermove", updateJoystick);
  function releasePointer(event) {
    if (event.pointerId === joystick.pointer) { joystick.pointer = null; joystick.x = 0; joystick.y = 0; ui.joystickKnob.style.transform = ""; if (playing) send({ type: "input", x: 0, y: 0 }); }
    if (event.pointerId === attackPointer) { attackPointer = null; attackHeld = false; ui.attackButton.classList.remove("held"); }
  }
  addEventListener("pointerup", releasePointer); addEventListener("pointercancel", releasePointer);
  ui.joystick.addEventListener("lostpointercapture", releasePointer); ui.attackButton.addEventListener("lostpointercapture", releasePointer);
  ui.attackButton.addEventListener("pointerdown", (event) => {
    if (!canControl()) return;
    event.preventDefault(); attackPointer = event.pointerId; attackHeld = true; ui.attackButton.setPointerCapture(event.pointerId); ui.attackButton.classList.add("held");
  });
  ui.attackButton.addEventListener("contextmenu", (event) => event.preventDefault());
  setInterval(() => {
    if (!playing || document.hidden || blurPaused) return;
    let x = 0, y = 0;
    if (canControl()) {
      x = Number(heldKeys.has("KeyD") || heldKeys.has("ArrowRight")) - Number(heldKeys.has("KeyA") || heldKeys.has("ArrowLeft")) + joystick.x;
      y = Number(heldKeys.has("KeyS") || heldKeys.has("ArrowDown")) - Number(heldKeys.has("KeyW") || heldKeys.has("ArrowUp")) + joystick.y;
      const length = Math.hypot(x, y); if (length > 1) { x /= length; y /= length; }
      if ((attackHeld || heldKeys.has("Space")) && performance.now() >= nextAttackAt) {
        if(selectedTarget && me.pvp_safety!==false){if(performance.now()-lastTargetWarning>1800){notice("Blokada PvP jest włączona. Wyłącz ją świadomie przed atakiem.","error");lastTargetWarning=performance.now();}}
        else send(selectedEnemy?{type:"attack",enemy_id:selectedEnemy}:selectedTarget?{type:"attack",target_id:selectedTarget}:{type:"attack"});
        nextAttackAt=performance.now()+200;
      }
    }
    send({ type: "input", x, y });
  }, 50);

  function seeded(seed) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }
  function ellipse(context,x,y,rx,ry,color){context.fillStyle=color;context.beginPath();context.ellipse(x,y,rx,ry,0,0,TAU);context.fill();}
  function line(context,points,color,width){context.strokeStyle=color;context.lineWidth=width;context.beginPath();points.forEach(([x,y],i)=>i?context.lineTo(x,y):context.moveTo(x,y));context.stroke();}
  function rounded(context,x,y,w,h,r,color){if(w<=0||h<=0)return;context.fillStyle=color;context.beginPath();context.roundRect(x,y,w,h,r);context.fill();}
  function block(g,x,y,w,h,color){g.fillStyle=color;g.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
  function pathDistance(x,y,points){let best=Infinity;for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i],dx=b[0]-a[0],dy=b[1]-a[1],q=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)));best=Math.min(best,Math.hypot(x-a[0]-q*dx,y-a[1]-q*dy));}return best;}
  function sameFloor(a,b){return (a?.floor||0)===(b?.floor||0);}
  function nearbyService(service){return (world.npcs||[]).find(n=>n.service===service&&sameFloor(me,n)&&distance(me,n)<=(n.radius||125));}
  function nearestMerchant(){return [world.merchant,...(world.npcs||[]).filter(n=>n.service==='merchant')].filter(Boolean).filter(n=>sameFloor(me,n)).sort((a,b)=>distance(me,a)-distance(me,b))[0]||world.merchant;}
  function nearestSite(){return (world.pois||[]).filter(s=>sameFloor(me,s)&&distance(me,s)<=s.radius).sort((a,b)=>distance(me,a)-distance(me,b))[0];}
  function nearestStair(){return (world.stairs||[]).filter(s=>sameFloor(me,s)&&distance(me,s)<=s.radius).sort((a,b)=>distance(me,a)-distance(me,b))[0];}
  function spellsForClass(){return Object.entries(world.spells||{}).filter(([,s])=>!s.class_ids||s.class_ids.includes(me?.class_id));}
  function spellAvailable(s){return me&&me.level>=s.min_level&&(!s.promotion||me.promoted);}
  function cast(id){if(playing&&me?.hp>0)send({type:'cast',spell_id:id});}
  function spellByLevel(level){return spellsForClass().find(([,s])=>s.min_level===level)?.[0];}
  function useBestPotion(prefix){
    const keys=Object.entries(world.potions||{}).filter(([k,s])=>k.startsWith(prefix)&&me?.potions?.[k]>0&&me.level>=(s.min_level||1)).sort((a,b)=>b[1].restore-a[1].restore);
    potion(keys[0]?.[0]||prefix);
  }
  function openExpansion(tab='spells'){expansionTab=tab;expansionSignature='';setPanel('progression');}
  function navigateTo(point,labelText){navigationGoal={...point,label:labelText||point.name};ui.sidePanel.hidden=true;notice(`Cel wyprawy: ${navigationGoal.label}`);updateHUD();}
  function guideRow(parent,title,detail,buttons=[]){
    const row=element('article','progress-entry');row.append(element('strong','',title),element('p','muted',detail));
    const actions=element('div','progress-actions');for(const b of buttons)actions.append(b);row.append(actions);parent.append(row);return row;
  }
  function renderExpansion(){
    if(!me)return;
    const services=['captain','bank','master','merchant'].map(s=>!!nearbyService(s));services[3]=merchantNear();
    const affordable=[...Object.values(world.spells||{}),...Object.values(world.runes||{})].map(s=>me.mana>=s.mana);
    const signature=JSON.stringify([expansionTab,me.level,me.promoted,me.skills,me.gold,me.bank_gold,me.depot,me.inventory,me.equipment,me.mastery,me.blessed,me.runes,affordable,me.soul,me.potions,me.home_city,me.hp>0,services,me.floor,Math.floor(me.x/64),Math.floor(me.y/64),Math.ceil(me.combat_remaining),Math.ceil(me.rune_cooldown),Object.entries(me.spell_cooldowns||{}).map(([k,v])=>[k,Math.ceil(v)]),me.discoveries,atlasMode,me.premium_demo,Math.ceil((me.premium_demo_remaining||0)/86400)]);
    if(signature===expansionSignature)return;expansionSignature=signature;
    const root=ui.progressionContent;root.replaceChildren();
    ui.progressionSubtitle.textContent=`${me.profession||className(me.class_id)} · poziom ${me.level} · dusza ${me.soul||0}/${me.max_soul||100}`;
    for(const b of ui.progressionNav.querySelectorAll('button'))b.classList.toggle('active',b.dataset.view===expansionTab);
    if(expansionTab==='spells'){
      root.append(element('p','panel-tip','Czary odblokowują się z poziomem. 3: leczenie · 4: przyspieszenie · 5: czar zaawansowany · 6: mistrzowski · 7: wybrana runa.'));
      for(const [id,s]of spellsForClass()){
        const cd=Math.ceil(me.spell_cooldowns?.[id]||0),ok=spellAvailable(s);
        const b=actionButton(cd?`${cd} s`:ok?'Rzuć czar':`Poziom ${s.min_level}`,()=>cast(id),!ok||cd>0||me.mana<s.mana||me.hp<=0);
        b.dataset.cast=id;
        guideRow(root,`${ok?'✦':'◇'} ${s.name} · ${s.words}`,`Poz. ${s.min_level}${s.promotion?' · promocja':''} · ${s.mana} many · ${s.cooldown} s. ${s.description}`,[b]);
      }
      root.append(element('div','section-label','RUNY · PRZENOŚNA MAGIA'));
      for(const[id,r]of Object.entries(world.runes||{})){
        const ok=me.level>=r.min_level,count=me.runes?.[id]||0;
        const use=actionButton('Użyj',()=>send({type:'rune_use',rune_id:id}),!ok||!count||me.rune_cooldown>0||me.hp<=0);use.dataset.rune=id;
        const craft=actionButton('Stwórz',()=>send({type:'rune_craft',rune_id:id}),!ok||!['mage','druid'].includes(me.class_id)||me.mana<r.mana||me.soul<r.soul||me.rune_cooldown>0||count>=99);
        const buy=actionButton(`Kup · ${r.price} zł`,()=>send({type:'rune_buy',rune_id:id}),!merchantNear()||me.combat_remaining>0||!ok||me.gold<r.price||count>=99);
        const select=actionButton(selectedRune===id?'✓ Skrót 7':'Pod skrót 7',()=>{selectedRune=id;expansionSignature='';renderExpansion();});
        guideRow(root,`${r.name} · ${count}/99`,`Poz. ${r.min_level}. Wytwarzanie: ${r.mana} many + ${r.soul} duszy; mag lub druid. Każda klasa może użyć zakupionej runy.`,[use,craft,buy,select]);
      }
    }else if(expansionTab==='growth'){
      root.append(element('div','section-label','UMIEJĘTNOŚCI ROSNĄ PRZEZ UŻYWANIE'));
      for(const[key,labelText]of Object.entries({melee:'Walka wręcz',distance:'Walka dystansowa',magic:'Poziom magiczny',shielding:'Obrona'})){
        const v=me.skills?.[key]||{level:10,progress:0,next:30},row=guideRow(root,`${labelText} · ${v.level}`,`${v.progress} / ${v.next} do następnego poziomu`);
        const track=element('div','skill-track'),bar=element('i');bar.style.width=`${Math.min(100,v.progress/v.next*100)}%`;track.append(bar);row.append(track);
      }
      root.append(element('div','section-label','KOLEJNE MOŻLIWOŚCI'));
      for(const m of world.milestones||[])guideRow(root,`${me.level>=m.level?'✓':'◇'} Poziom ${m.level} · ${m.name}`,m.description);
      const can=!!nearbyService('master')&&!me.combat_remaining;
      guideRow(root,'Promocja profesji',me.promoted?'Masz wyższą rangę. Szybsza regeneracja i limit 200 punktów duszy.':'Poziom 20 · 2000 złota · porozmawiaj z mistrzem w mieście.',[actionButton(me.promoted?'✓ Promowany':'Kup promocję',()=>send({type:'promote'}),!can||me.promoted||me.level<20||me.gold<2000)]);
      root.append(element('p','muted',`Punkty specjalizacji: ${me.mastery_points||0}. Pierwszy na poziomie 50, kolejne co 5 poziomów. Wymagana promocja i mistrz.`));
      for(const[key,name,detail]of[['power','Siła','+3 do ataku'],['vitality','Witalność','+12 maksymalnego zdrowia'],['focus','Skupienie','+8 maksymalnej many i +1 do ataku']])guideRow(root,`${name} · ${me.mastery?.[key]||0}/20`,detail,[actionButton('Dodaj punkt',()=>send({type:'mastery',branch:key}),!can||!me.mastery_points||(me.mastery?.[key]||0)>=20)]);
      root.append(actionButton('Wyzeruj specjalizację · 200 zł',()=>send({type:'mastery_reset'}),!can||me.gold<200));
    }else if(expansionTab==='atlas'){
      root.append(element('p','panel-tip','20 krain · 5 odległych miast · 11 dwupiętrowych podziemi. Poziomy krain to zalecenie. Kliknij miejsce na mapie albo wybierz cel poniżej. Nawigacja wskazuje kierunek; nie prowadzi automatycznie.'));
      const map=document.createElement('canvas');map.id='atlasCanvas';map.width=700;map.height=505;map.className='atlas-canvas';root.append(map);ui.atlasCanvas=map;
      drawAtlas(map);map.addEventListener('click',event=>{const box=map.getBoundingClientRect(),x=(event.clientX-box.left)/box.width*world.width,y=(event.clientY-box.top)/box.height*world.height;const poi=[...(world.cities||[]),...(world.stairs||[]).filter(s=>s.floor===0)].sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0];navigateTo(poi&&Math.hypot(poi.x-x,poi.y-y)<4500?poi:{x,y,floor:0,name:'Punkt na mapie'});});
      const filters=element('div','progress-actions');for(const[id,labelText]of[['nearby','Okolica'],['regions','Krainy'],['cities','Miasta'],['caves','Podziemia']])filters.append(actionButton(labelText,()=>{atlasMode=id;expansionSignature='';renderExpansion();},false,atlasMode===id?'active':''));root.append(filters);
      guideRow(root,'Wysokości i łupy','Schody E: piętra −2, −1, 0, +1, +2, +3. Źródła leczą; kamienie wiatru przyspieszają; kapliczki chronią przed potworami. Skrytki odnawiają się co 30 min. Łupy: wyposażenie 12%, trofeum 24%, mikstura 7%; uprawnione gatunki mają 1,5% szansy na przedmiot rodowy. Boss: 100% wyposażenie, 80% trofeum, 35% mikstura, do 8% przedmiot rodowy; boss 110+: 0,2% legendarny relikt. Rzuty są niezależne.');
      const rows=atlasMode==='nearby'?(world.landmarks||[]).filter(l=>l.hint||me.discoveries?.includes(l.id)).sort((a,b)=>distance(me,a)-distance(me,b)).slice(0,14):atlasMode==='cities'?world.cities:atlasMode==='caves'?(world.stairs||[]).filter(s=>s.floor===0):world.regions;
      for(const item of rows||[]){
        const goal=atlasMode==='regions'?{x:item.x+item.w/2,y:item.y+item.h/2,floor:0}:item;
        const danger=item.recommended_level?`Zalecany poz. ${item.recommended_level} · `:item.min_level?`Zalecany poz. ${item.min_level}–${item.max_level||item.min_level} · `:'';
        const time=Math.ceil(distance(me,goal)/(me.speed||100)/60);
        guideRow(root,item.name,`${danger}${item.description||''} ${directionTo(goal)} · ≥${time} min marszu${!sameFloor(me,goal)?' · inne piętro':''}`,[actionButton('Wyznacz kierunek',()=>navigateTo(goal,item.name))]);
      }
      root.append(actionButton('Usuń cel nawigacji',()=>{navigationGoal=null;updateHUD();}));
    }else if(expansionTab==='premium'){
      guideRow(root,'Premium · szybki marsz','10 zł / miesiąc · +20% szybkości ruchu. Teraz to bezpłatna symulacja: nic nie płacisz, nie podajesz karty, nie ma automatycznego odnowienia.');
      guideRow(root,me.premium_demo?'Testowe premium aktywne':'Wypróbuj szybki marsz',me.premium_demo?`Pozostało ${Math.ceil(me.premium_demo_remaining/86400)} dni. Bonus łączy się z podłożem i czarem przyspieszenia.`:'Włącz na 30 dni; możesz w każdej chwili wyłączyć.',[actionButton(me.premium_demo?'Wyłącz symulację':'Włącz bezpłatną symulację',()=>send({type:'premium_demo',enabled:!me.premium_demo}))]);
      guideRow(root,'Podłoże ma znaczenie','Ścieżka +18% · kamień +25% · trawa normalnie · ściółka −6% · piasek −14% · śnieg −12% · błoto −28%. Podłoże wpływa również na potwory.');
    }else{
      const safe=me.hp>0&&!me.combat_remaining,bank=nearbyService('bank'),master=nearbyService('master'),captain=nearbyService('captain');
      root.append(element('p','panel-tip',me.combat_remaining>0?'Trwa blokada po walce. Zaczekaj przed usługami.':'Usługi wymagają rozmowy z odpowiednim mieszkańcem. Atlas pokazuje miasta.'));
      const city=(world.cities||[]).filter(c=>sameFloor(me,c)).sort((a,b)=>distance(me,a)-distance(me,b))[0];
      for(const[service,labelText]of[['captain','Kapitan — podróże'],['bank','Bankier — depozyt i odrodzenie'],['master','Mistrz — promocja i błogosławieństwo'],['merchant','Kupiec — zapasy']]){
        const n=service==='merchant'?nearestMerchant():(world.npcs||[]).filter(n=>n.service===service).sort((a,b)=>distance(me,a)-distance(me,b))[0];
        if(n)root.append(actionButton(`${labelText} · ${directionTo(n)}`,()=>navigateTo(n,n.name)));
      }
      root.append(element('div','section-label','STATKI · OD POZIOMU 8'));
      for(const c of world.cities||[]){
        const cost=40+Math.floor(distance(me,c)/1000)*8;
        guideRow(root,c.name,`Rejs: ${cost} złota${captain?'':' · podejdź do kapitana'}`,[actionButton('Wypłyń',()=>send({type:'travel',city_id:c.id}),!captain||!safe||me.level<8||me.gold<cost||captain?.city_id===c.id)]);
      }
      guideRow(root,`Bank · ${formatNumber(me.bank_gold)} złota`,'Złoto w banku i przedmioty w depozycie nie przepadają przy śmierci.',[
        actionButton('Wpłać wszystko',()=>send({type:'bank_deposit',amount:'all'}),!bank||!safe||me.gold<1),
        actionButton('Wypłać 100',()=>send({type:'bank_withdraw',amount:100}),!bank||!safe||me.bank_gold<100),
        actionButton('Wypłać wszystko',()=>send({type:'bank_withdraw',amount:'all'}),!bank||!safe||me.bank_gold<1)]);
      guideRow(root,'Miejsce odrodzenia',(world.cities||[]).find(c=>c.id===me.home_city)?.name||'Przystań',[actionButton('Przenieś odrodzenie tutaj',()=>send({type:'bind_city'}),!bank||!safe||bank?.city_id===me.home_city)]);
      guideRow(root,'Błogosławieństwo',me.blessed?'Aktywne do następnej śmierci. Czerwona czaszka wyłącza ochronę.':'Poz. 40 · 500 zł · połowa zwykłej kary złota i PD przy następnej śmierci.',[actionButton('Kup błogosławieństwo',()=>send({type:'bless'}),!master||!safe||me.level<40||me.gold<500||me.blessed)]);
      root.append(element('div','section-label',`DEPOZYT · ${(me.depot||[]).length}/120`));
      for(const item of me.inventory||[])if(!Object.values(me.equipment||{}).includes(item.uid))guideRow(root,item.name,'W plecaku',[actionButton('Odłóż do depozytu',()=>send({type:'depot_store',uid:item.uid}),!bank||!safe||(me.depot||[]).length>=120)]);
      for(const item of me.depot||[])guideRow(root,item.name,'W depozycie',[actionButton('Zabierz',()=>send({type:'depot_take',uid:item.uid}),!bank||!safe||(me.inventory||[]).length>=40)]);
      root.append(element('div','section-label','MIKSTURY NA DALSZE WYPRAWY'));
      for(const[id,s]of Object.entries(world.potions||{})){
        const count=me.potions?.[id]||0;
        guideRow(root,`${s.name} · ${count}/99`,`Poz. ${s.min_level||1} · odnawia ${s.restore} · ${s.price} złota. Skróty 1 i 2 używają najsilniejszej posiadanej mikstury.`,[actionButton('Kup',()=>send({type:'buy',item:id}),!merchantNear()||!safe||me.level<(s.min_level||1)||me.gold<s.price||count>=99)]);
      }
    }
  }
  function drawAtlas(canvas){
    if(!canvas)return;const g=canvas.getContext('2d'),sx=canvas.width/world.width,sy=canvas.height/world.height;
    g.fillStyle='#192728';g.fillRect(0,0,canvas.width,canvas.height);
    for(const r of world.regions||[]){g.fillStyle=r.color;g.fillRect(r.x*sx,r.y*sy,r.w*sx,r.h*sy);g.fillStyle='#10191670';g.fillRect(r.x*sx,r.y*sy,r.w*sx,r.h*sy);g.strokeStyle='#eeeecc25';g.strokeRect(r.x*sx,r.y*sy,r.w*sx,r.h*sy);g.fillStyle='#e9e4c7';g.textAlign='center';g.font='12px system-ui';const words=r.name.split(' ');g.fillText(words.slice(0,2).join(' '),(r.x+r.w/2)*sx,(r.y+r.h/2)*sy-8);g.fillText(words.slice(2).join(' '),(r.x+r.w/2)*sx,(r.y+r.h/2)*sy+7);g.fillStyle='#d8c888';g.font='10px system-ui';g.fillText(`${r.min_level}–${r.max_level}`,(r.x+r.w/2)*sx,(r.y+r.h/2)*sy+22);}
    g.strokeStyle='#dfc89070';g.lineWidth=1;for(const road of world.roads||[])line(g,road.map(([x,y])=>[x*sx,y*sy]),'#cfc08465',1);
    for(const r of world.waterways||[])line(g,[r.a,r.b].map(([x,y])=>[x*sx,y*sy]),'#67b4c7',2);
    for(const s of world.stairs||[])if(s.floor===0){g.fillStyle='#ddb8e9';g.fillRect(s.x*sx-3,s.y*sy-3,6,6);}
    for(const c of world.cities||[]){ellipse(g,c.x*sx,c.y*sy,5,5,'#ffd989');g.font='bold 11px system-ui';g.textAlign=c.x*sx<70?'left':'center';g.fillStyle='#fff1c8';g.fillText(c.name,Math.max(7,c.x*sx),Math.max(15,c.y*sy-10));}
    if(me){ellipse(g,me.x*sx,me.y*sy,4,4,'#fff');g.strokeStyle='#163123';g.strokeRect(me.x*sx-5,me.y*sy-5,10,10);}
    if(navigationGoal){g.strokeStyle='#ffe392';g.beginPath();g.arc(navigationGoal.x*sx,navigationGoal.y*sy,8,0,TAU);g.stroke();}
  }
  function buildStaticIndex(){
    surfaceMap=new Runtime.SurfaceMap(world);
    roads=(world.roads||[]).filter(path=>path.some(([x,y])=>x<3400&&y<2500));
    const entries=[];
    for(const [kind,list] of [['obstacle',world.obstacles],['landmark',world.landmarks],['npc',world.npcs],['merchant',[world.merchant]],['stair',world.stairs],['camp',world.hunting_grounds],['waterway',world.waterways],['bridge',world.bridges],['elevation',world.elevations]]){
      (list||[]).forEach((data,index)=>{if(!data)return;entries.push({kind,data,index,order:entries.length,floor:data.floor||0,left:data.x-200,top:data.y-220,right:data.x+(data.w||0)+200,bottom:data.y+(data.h||0)+220});});
    }
    staticIndex=new Runtime.SpatialIndex(entries);staticStamp='';staticCandidates=[];minimapSnapshot=null;
  }
  function nearbyDrawables(){
    const halfW=viewport.w/camera.scale/2,halfH=viewport.h/camera.scale/2,cx=Math.floor(camera.x/512),cy=Math.floor(camera.y/512),floor=me?.floor||0;
    const stamp=`${cx}:${cy}:${floor}:${viewport.w}:${viewport.h}:${camera.scale}`;
    if(stamp!==staticStamp){staticStamp=stamp;staticCandidates=staticIndex?staticIndex.query(cx*512-halfW,cy*512-halfH,(cx+1)*512+halfW,(cy+1)*512+halfH,floor):[];}
    return staticCandidates;
  }
  function trimChunks(){
    for(const key of groundChunks.keys()){
      if(groundChunks.size<=chunkLimit)break;
      if(!protectedChunks.has(key)){groundChunks.get(key).width=1;groundChunks.delete(key);}
    }
  }
  function prepareGroundAhead(x0,y0,x1,y1,floor){
    const stamp=`${x0}:${y0}:${x1}:${y1}:${floor}`;
    if(stamp!==warmStamp){
      warmStamp=stamp;warmQueue=[];
      for(let y=Math.max(0,y0-1);y<=Math.min(Math.ceil(world.height/512)-1,y1+1);y++)for(let x=Math.max(0,x0-1);x<=Math.min(Math.ceil(world.width/512)-1,x1+1);x++){
        if(floor===0&&(x+1)*512<=3200&&(y+1)*512<=2304)continue;
        if(!groundChunks.has(`${floor}:${x}:${y}`))warmQueue.push([x,y,floor]);
      }
      warmQueue.sort((a,b)=>Math.hypot(a[0]*512+256-camera.x,a[1]*512+256-camera.y)-Math.hypot(b[0]*512+256-camera.x,b[1]*512+256-camera.y));
    }
    if(warmScheduled||!warmQueue.length||document.hidden)return;
    warmScheduled=true;
    const work=()=>{
      warmScheduled=false;if(document.hidden)return;
      const point=warmQueue.shift();if(!point)return;
      const [x,y,f]=point,key=`${f}:${x}:${y}`;
      if(!groundChunks.has(key))groundChunks.set(key,makeGroundChunk(x,y,f));
      trimChunks();
    };
    if(globalThis.requestIdleCallback)requestIdleCallback(work,{timeout:120});else setTimeout(work,0);
  }
  function makeGroundChunk(cx,cy,floor){
    const c=document.createElement('canvas');c.width=c.height=512;const g=c.getContext('2d');
    const ox=cx*512,oy=cy*512,random=seeded((cx*73856093^cy*19349663^floor*83492791)>>>0);
    const palettes={forest:['#527b42','#598449','#507a47'],meadow:['#7dab4f','#80a951','#86ae54'],swamp:['#63887a','#688c7d','#5c8378'],desert:['#cbb273','#d4bb7b','#c8ac72'],snow:['#c6dadd','#bfd4da','#d5e2e1'],lava:['#79584e','#865e4e','#81584f'],obsidian:['#635b73','#6c627d','#695f75'],mountain:['#93988b','#8e9489','#a0a194'],ruins:['#879584','#8f9b8b','#929987'],orc:['#a19161','#a99a66','#988759']};
    const rooms=[...(world.dungeons||[]),...(world.elevations||[])].filter(d=>d.floor===floor).flatMap(d=>d.rooms);

    for(let yy=0;yy<512;yy+=32)for(let xx=0;xx<512;xx+=32){
      const x=ox+xx,y=oy+yy,noise=random(),region=(world.regions||[]).find(r=>x>=r.x&&x<r.x+r.w&&y>=r.y&&y<r.y+r.h),palette=palettes[region?.biome]||palettes.meadow;
      if(floor<0){
        const room=rooms.some(r=>x+16>=r.x&&x+16<=r.x+r.w&&y+16>=r.y&&y+16<=r.y+r.h);
        block(g,xx,yy,32,32,room?(noise>.5?'#8c8278':'#837a73'):'#282b32');
        if(room){block(g,xx+1,yy+1,30,1,'#b2a18b');block(g,xx+2,yy+31,29,1,'#5a5554');if(noise>.8)line(g,[[xx+5,yy+4],[xx+14,yy+13],[xx+12,yy+23]],'#605c59',1);}else{block(g,xx+2,yy+2,28,20,'#34373e');block(g,xx+2,yy+2,28,2,'#45464d');}continue;
      }
      block(g,xx,yy,32,32,palette[Math.floor(noise*palette.length)]);
      const raised=floor>0&&rooms.some(r=>x+16>=r.x&&x+16<=r.x+r.w&&y+16>=r.y&&y+16<=r.y+r.h);
      const surface=raised?'stone':surfaceMap?.at(x+16,y+16)||'grass',road=surface==='path',city=(world.cities||[]).some(c=>Math.hypot(x-c.x,y-c.y)<205);
      if(road||city){block(g,xx,yy,32,32,city?'#aaa78e':'#b5a174');for(let k=0;k<3;k++){block(g,xx+2+k*10,yy+2,8,13,'#c5b58a');block(g,xx+2+k*10,yy+18,8,12,'#c1b286');}}
      else {
        const base=world.surfaces?.[surface]?.color;if(base&&surface!=='grass')block(g,xx,yy,32,32,base);
        if(surface==='mud'){ellipse(g,xx+13,yy+17,11,5,'#6e6453');line(g,[[xx+7,yy+14],[xx+16,yy+14]],'#a29776',1);}
        if(surface==='stone'){line(g,[[xx+2,yy+2],[xx+26,yy+2],[xx+29,yy+19]],'#c3c1a8',1);line(g,[[xx+4,yy+29],[xx+23,yy+29]],'#737c75',2);}
        for(let k=0;k<3;k++){const tx=xx+random()*27,ty=yy+random()*27;block(g,tx,ty,2,3,region?.biome==='snow'?'#e7eeee':region?.biome==='lava'?'#c17b58':'#a8b078');}if(noise>.94){const color=region?.biome==='lava'?'#ee9163':region?.biome==='snow'?'#eff5ed':'#dbca9b';block(g,xx+15,yy+14,4,4,color);}}
    }
    return c;
  }
  function drawGround(){
    const floor=me?.floor||0,x0=Math.max(0,Math.floor((camera.x-viewport.w/camera.scale/2)/512)),y0=Math.max(0,Math.floor((camera.y-viewport.h/camera.scale/2)/512)),x1=Math.min(Math.ceil(world.width/512)-1,Math.floor((camera.x+viewport.w/camera.scale/2)/512)),y1=Math.min(Math.ceil(world.height/512)-1,Math.floor((camera.y+viewport.h/camera.scale/2)/512));
    chunkLimit=Math.max(32,(x1-x0+3)*(y1-y0+3));protectedChunks=new Set();
    for(let cy=y0;cy<=y1;cy++)for(let cx=x0;cx<=x1;cx++)protectedChunks.add(`${floor}:${cx}:${cy}`);
    for(let cy=y0;cy<=y1;cy++)for(let cx=x0;cx<=x1;cx++){
      if(floor===0&&(cx+1)*512<=3200&&(cy+1)*512<=2304)continue;
      const key=`${floor}:${cx}:${cy}`;let chunk=groundChunks.get(key);if(!chunk){chunk=makeGroundChunk(cx,cy,floor);groundChunks.set(key,chunk);}else{groundChunks.delete(key);groundChunks.set(key,chunk);}
      ctx.drawImage(chunk,cx*512,cy*512);
    }
    trimChunks();prepareGroundAhead(x0,y0,x1,y1,floor);
    if(!floor&&ground&&camera.x-viewport.w/camera.scale/2<3200&&camera.y-viewport.h/camera.scale/2<2304)ctx.drawImage(ground,0,0);
    if(floor>0)for(const entry of nearbyDrawables())if(entry.kind==='elevation')drawCliff(entry.data,true);
    if(floor<0){for(const d of world.dungeons||[])if(d.floor===floor&&inView(d.x+d.w/2,d.y+d.h/2,d.w)){for(const r of d.rooms){ctx.strokeStyle='#d0b88a55';ctx.lineWidth=2;ctx.strokeRect(r.x,r.y,r.w,r.h);}}}
  }
  function drawStair(s){
    if(!sameFloor(me,s)||!inView(s.x,s.y))return;
    const x=s.x,y=s.y,down=s.to_floor<s.floor;
    ellipse(ctx,x,y,32,23,'#25232b');for(let i=0;i<5;i++){block(ctx,x-22+i*3,y-14+i*6,44-i*6,5,down?'#a79777':'#d1be95');block(ctx,x-22+i*3,y-14+i*6,44-i*6,1,'#ead39c');}
    label(`${down?'▼':'▲'} ${s.to_floor>0?'+':''}${s.to_floor} · ${s.name}`,x,y-34,'#ead3ff',10);if(me&&distance(me,s)<100)label(`[E] ${s.min_level>me.level?'Wymagany poziom '+s.min_level:'Przejdź'}`,x,y+29,'#ffe099',11);
  }
  function drawCamp(c,t){
    if(!sameFloor(me,c)||!inView(c.x,c.y,350))return;
    const x=c.x,y=c.y,deco=c.decoration||'den';
    if(deco==='camp'){
      block(ctx,x-16,y-8,32,18,'#75634d');block(ctx,x-13,y-11,26,15,'#b89b6b');fire(x,y-8,t,.6);
      for(const[dx,dy]of[[-82,18],[101,-28]]){block(ctx,x+dx-22,y+dy-45,44,25,'#443e35');ctx.fillStyle='#a58858';ctx.beginPath();ctx.moveTo(x+dx-26,y+dy-46);ctx.lineTo(x+dx,y+dy-82);ctx.lineTo(x+dx+26,y+dy-46);ctx.fill();block(ctx,x+dx-7,y+dy-44,14,23,'#403b32');}
      block(ctx,x-75,y+52,51,16,'#89683e');for(const dx of[-70,-32]){ellipse(ctx,x+dx,y+72,10,10,'#594832');ellipse(ctx,x+dx,y+72,5,5,'#bd965b');}
    }else if(deco==='web'){
      for(const[dx,dy]of[[-75,12],[25,-50],[82,30]]){const xx=x+dx,yy=y+dy;for(let i=0;i<8;i++){const a=i/8*TAU;line(ctx,[[xx,yy],[xx+Math.cos(a)*43,yy+Math.sin(a)*25]],'#e2e3c080',1);}for(const r of[12,24,39]){ctx.strokeStyle='#e2e3c095';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(xx,yy,r,r*.58,0,0,TAU);ctx.stroke();}}block(ctx,x-15,y+15,13,23,'#dfdec0');
    }else if(deco==='den'){
      ellipse(ctx,x,y,53,27,'#665b45');ellipse(ctx,x+4,y-2,39,19,'#2d382a');for(const[dx,dy]of[[-55,24],[35,-13],[6,44]]){line(ctx,[[x+dx-14,y+dy],[x+dx+17,y+dy-7]],'#bcac78',3);block(ctx,x+dx,y+dy-5,5,8,'#e2d7b4');}
    }else if(deco==='crypt'||deco==='ruin'){
      for(const[dx,dy]of[[-67,-34],[25,11],[76,-42],[-12,49]]){block(ctx,x+dx-14,y+dy-31,28,36,'#838b82');block(ctx,x+dx-12,y+dy-34,24,8,'#c4c4ac');line(ctx,[[x+dx,y+dy-25],[x+dx,y+dy-7]],'#585e59',3);line(ctx,[[x+dx-6,y+dy-19],[x+dx+6,y+dy-19]],'#585e59',2);}block(ctx,x-23,y-14,39,24,'#454b46');
    }else if(deco==='reeds'){
      ellipse(ctx,x,y,76,30,'#4a7873');ellipse(ctx,x-9,y-3,56,19,'#75a99b');for(let i=0;i<15;i++){const dx=Math.sin(i*7)*86,dy=Math.cos(i*3)*38;line(ctx,[[x+dx,y+dy],[x+dx-3,y+dy-32]],'#63774b',2);block(ctx,x+dx-5,y+dy-36,5,10,'#b59a65');}
    }else if(deco==='rift'||deco==='crystals'){
      for(const[dx,dy]of[[-57,-14],[31,-21],[5,29]]){ctx.fillStyle=deco==='rift'?'#bd7aca':'#aae3e7';ctx.beginPath();ctx.moveTo(x+dx-11,y+dy);ctx.lineTo(x+dx-5,y+dy-48);ctx.lineTo(x+dx+7,y+dy-64);ctx.lineTo(x+dx+17,y+dy-9);ctx.fill();line(ctx,[[x+dx+7,y+dy-58],[x+dx+7,y+dy-9]],'#e2e3d4',2);}
    }else{
      if(deco==='quarry'){for(let i=3;i>=0;i--){ellipse(ctx,x,y+i*7,126-i*15,73-i*9,i%2?'#949d88':'#bac0a4');}for(let i=0;i<4;i++)block(ctx,x-17,y+35+i*10,34,7,'#c9c5a6');}
      for(const[dx,dy]of[[-57,0],[45,-23],[15,37]]){ellipse(ctx,x+dx,y+dy,25,16,'#797c73');block(ctx,x+dx-17,y+dy-14,28,6,'#c0bc9f');}
      if(deco==='bones'){for(let i=0;i<6;i++)line(ctx,[[x-35+i*11,y-10],[x-32+i*11,y+16]],'#e1d2a7',4);ellipse(ctx,x+41,y+4,17,11,'#d1c3a3');block(ctx,x+44,y-1,5,5,'#57544d');}
    }
    if(c.name)label(c.name,x,y-108,'#ead8a9',10);
  }

  function drawNewCreature(v,t,spec){
    const x=v.x,y=v.y,dragon=spec.appearance==='dragon',boss=spec.boss,color=spec.color||'#d18573';
    if(!inView(x,y)||v.entity.hp<=0)return;
    ctx.save();ctx.translate(x,y);ctx.scale(spec.size||1,spec.size||1);ellipse(ctx,0,4,28,11,'#20232666');
    const wing=Math.sin(t*4+x)*6;
    for(const side of[-1,1]){ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(side*8,-35);ctx.lineTo(side*55,-65-wing);ctx.lineTo(side*42,-20);ctx.lineTo(side*17,-9);ctx.closePath();ctx.fill();line(ctx,[[side*8,-35],[side*55,-65-wing],[side*31,-25]],'#553f54',2);block(ctx,side*11-4,-1,10,12,'#68535e');}
    block(ctx,-17,-38,34,39,color);block(ctx,-11,-33,21,24,dragon?'#d3b878':'#bca3bf');block(ctx,-13,-61,27,26,color);block(ctx,-18,-66,7,16,'#d9c88e');block(ctx,12,-66,7,16,'#d9c88e');block(ctx,-8,-54,5,4,'#fff088');block(ctx,5,-54,5,4,'#fff088');block(ctx,-5,-44,14,3,'#3d3541');if(dragon)line(ctx,[[-8,-7],[-30,4],[-54,-4]],color,10);ctx.restore();
    const yy=y-85*(spec.size||1);label(v.entity.name,x,yy,'#ffddb7',11);block(ctx,x-26,yy+9,52,5,'#3b323a');block(ctx,x-25,yy+10,50*v.entity.hp/v.entity.max_hp,3,'#e8896c');
  }

  let roads=[[[560,1180],[620,900],[650,640],[900,580],[1210,580],[1305,340]],[[560,1180],[1000,1180],[1490,1150],[1700,1150],[2060,1120],[2300,900],[2550,500],[2590,370]],[[560,1180],[600,1350],[820,1490]],[[560,1180],[450,1460],[340,1640]],[[2050,1120],[2050,1460],[1870,1710]],[[2080,1140],[2500,1340],[2530,1630],[2530,1930]],[[430,1130],[740,1180],[740,1260]]];
  function buildGround(){
    groundChunks.clear();warmQueue=[];warmStamp="";
    ground=document.createElement("canvas");ground.width=3200;ground.height=2304;
    const g=ground.getContext("2d"),random=seeded(933742),tile=32,starterZones=[...(world.zones||[])].reverse();
    for(let y=0;y<2304;y+=tile)for(let x=0;x<3200;x+=tile){
      const noise=random(),zone=starterZones.find(z=>x>=z.x&&x<z.x+z.w&&y>=z.y&&y<z.y+z.h),id=zone?.id;
      let palette=["#76a94c","#7bad50","#77a74c","#7bac4d","#72a247"];
      if(id==="forest")palette=["#5b9746","#639d4b","#629a48","#5a9446"];
      if(id==="meadow")palette=["#8abb54","#8dbe58","#90bc55","#85b750"];
      if(id==="swamp")palette=["#6da78b","#68a28d","#72ab8e","#6ba483"];
      if(id==="ruins")palette=["#a2ab83","#9eab7e","#aeb193","#a6af8b"];
      if(id==="goblin_camp")palette=["#a5a062","#aaa265","#a3a25e","#969c5b"];
      if(id==="sanctuary")palette=["#8b9190","#919692","#858e89","#959992"];
      block(g,x,y,tile,tile,palette[Math.floor(noise*palette.length)]);
      const surface=surfaceMap?.at(x+16,y+16),path=surface?surface==='path':roads.some(points=>pathDistance(x+16,y+16,points)<33);
      const plaza=Math.hypot(x+16-560,y+16-1180)<205;
      if(path||plaza){
        const cobble=plaza||id==="sanctuary"||id==="ruins";
        block(g,x,y,32,32,cobble?"#9c967b":"#bda769");
        for(let r=0;r<2;r++)for(let c=0;c<3;c++){
          const xx=x+c*12-(r%2)*6,yy=y+r*16;
          block(g,xx+1,yy+1,10,14,cobble?["#b9b49b","#c4bfa6","#ada88e"][Math.floor(random()*3)]:["#ccb67b","#c7b477","#c3ac6e"][Math.floor(random()*3)]);
          block(g,xx+2,yy+2,8,1,cobble?"#d4cdb0":"#d9c58a");
        }
      }else{
        for(let k=0;k<5;k++){
          const xx=x+Math.floor(random()*30),yy=y+Math.floor(random()*29);
          block(g,xx,yy,2,4,id==="swamp"?"#478b70":"#63943d");block(g,xx+2,yy-2,2,3,id==="forest"?"#81ae56":"#a3ca6b");
        }
        if(random()>.78&&id!=="sanctuary"){
          const xx=x+7+Math.floor(random()*19),yy=y+7+Math.floor(random()*19),flower=["#ffe69b","#dba7ed","#f8f0c2","#6bbfe2","#f19b83"][Math.floor(random()*5)];
          block(g,xx,yy+1,2,6,"#477837");block(g,xx-2,yy,6,2,flower);block(g,xx,yy-2,2,6,flower);block(g,xx,yy,2,2,"#f4cc61");
        }
      }
    }
    // Walkable shallow pools and broken paving give each region its own floor language.
    for(let i=0;i<32;i++){
      const x=1745+random()*430,y=1400+random()*550;
      if(roads.some(p=>pathDistance(x,y,p)<45))continue;
      ellipse(g,x,y,17+random()*28,8+random()*14,"#527f7a");ellipse(g,x,y-2,15+random()*24,7+random()*11,"#64aaa3");
      block(g,x-10,y-2,12,2,"#a4d4b1");block(g,x+9,y+5,7,2,"#a6d08c");
      for(let k=0;k<3;k++){block(g,x+20+k*4,y-15-k*2,2,21,"#537f4d");block(g,x+20+k*4,y-15-k*2,3,7,"#c4ab64");}
    }
    for(let i=0;i<100;i++){
      const x=2100+random()*830,y=340+random()*630;if(roads.some(p=>pathDistance(x,y,p)<35))continue;
      block(g,x,y,15+random()*19,11+random()*16,"#848f77");block(g,x+2,y+1,14+random()*16,7+random()*14,"#c1bca3");line(g,[[x+8,y+3],[x+11,y+8],[x+8,y+12]],"#94997d",2);
    }
    // Scattered low flowers and shrubs are walkable; trunks and houses use server colliders.
    for(let i=0;i<360;i++){
      const x=40+random()*(3200-80),y=40+random()*(2304-80);
      if(x>1450&&x<1720||Math.hypot(x-560,y-1180)<245||roads.some(p=>pathDistance(x,y,p)<45))continue;
      const color=y>1370&&x>1720&&x<2230?"#609b76":"#61963f";
      block(g,x-7,y-2,16,6,"#52793466");block(g,x-9,y-6,8,5,color);block(g,x-2,y-10,10,10,color);block(g,x+6,y-5,8,6,color);block(g,x-1,y-10,6,3,"#a0c468");
      if(i%3===0){block(g,x-6,y-5,3,3,"#e6b472");block(g,x+7,y-3,3,3,"#e9c479");}
    }
    // Small cropped plots and fountain paving remain fully traversable.
    for(let y=1250;y<1285;y+=9)for(let x=345;x<420;x+=12){block(g,x,y,8,6,"#8b773f");block(g,x+2,y,4,5,"#92b848");block(g,x+3,y-1,3,3,"#db9046");}
  }
  function resize(){viewport={w:innerWidth,h:innerHeight,dpr:Math.min(devicePixelRatio||1,2)};canvas.width=Math.round(viewport.w*viewport.dpr);canvas.height=Math.round(viewport.h*viewport.dpr);camera.scale=viewport.w<560?1:viewport.h<620?.95:1.2;ctx.imageSmoothingEnabled=false;}
  addEventListener("resize",resize);resize();buildGround();
  function inView(x,y,margin=100){return Math.abs(x-camera.x)<viewport.w/camera.scale/2+margin&&Math.abs(y-camera.y)<viewport.h/camera.scale/2+margin;}
  function glow(x,y,radius,color,strength=.2){ctx.save();ctx.globalAlpha=strength;const gradient=ctx.createRadialGradient(x,y,0,x,y,radius);gradient.addColorStop(0,color);gradient.addColorStop(1,"transparent");ctx.fillStyle=gradient;ctx.fillRect(x-radius,y-radius,radius*2,radius*2);ctx.restore();}
  function label(text,x,y,color="#f7efc8",size=11){ctx.font=`600 ${size}px system-ui,sans-serif`;ctx.textAlign="center";ctx.textBaseline="middle";ctx.lineWidth=3;ctx.strokeStyle="#253323e8";ctx.lineJoin="round";ctx.strokeText(text,x,y);ctx.fillStyle=color;ctx.fillText(text,x,y);}
  function drawWaterways(t){
    const entries=nearbyDrawables(),water=entries.filter(e=>e.kind==='waterway');
    ctx.save();ctx.lineCap='round';ctx.lineJoin='round';
    for(const [extra,color]of [[22,'#b9bb77'],[10,'#62a890'],[0,'#449ead'],[-28,'#438fa6']])for(const {data:r}of water)line(ctx,[r.a,r.b],color,r.width+extra);
    for(const {data:r}of water){const x=(r.a[0]+r.b[0])/2,y=(r.a[1]+r.b[1])/2;for(let i=-1;i<2;i++){const xx=x+i*38,yy=y+Math.sin(t*1.5+x+i)*4;line(ctx,[[xx-12,yy],[xx,yy],[xx+7,yy-3]],'#a0d5c88c',2);}}
    for(const {kind,data:r}of entries)if(kind==='bridge'){
      line(ctx,[r.a,r.b],'#685336',r.width+8);line(ctx,[r.a,r.b],'#bc9255',r.width);
      const dx=r.b[0]-r.a[0],dy=r.b[1]-r.a[1],len=Math.hypot(dx,dy)||1,nx=-dy/len,ny=dx/len;
      for(let d=0;d<len;d+=12){const x=r.a[0]+dx*d/len,y=r.a[1]+dy*d/len;line(ctx,[[x-nx*65,y-ny*65],[x+nx*65,y+ny*65]],'#e0b574',2);}
      for(const side of[-1,1])line(ctx,[[r.a[0]+nx*69*side,r.a[1]+ny*69*side],[r.b[0]+nx*69*side,r.b[1]+ny*69*side]],'#795b35',5);
    }
    ctx.restore();
  }
  function drawCliff(r,edgeOnly=false){
    const {x,y,w,h}=r,face=edgeOnly?y+h:y+h-48;
    if(!edgeOnly){block(ctx,x+8,y+12,w,h,'#34453866');block(ctx,x,y,w,h,'#899083');block(ctx,x+5,y+5,w-10,h-52,'#aaa895');
      for(let xx=x+12;xx<x+w-12;xx+=49)for(let yy=y+12;yy<y+h-60;yy+=42){line(ctx,[[xx,yy],[Math.min(x+w-8,xx+31),yy],[xx+27,yy+17]],'#c4bea4',2);}}
    block(ctx,x,face,w,48,'#646e69');block(ctx,x,face,w,5,'#d1c8a9');
    for(let yy=face+10;yy<face+46;yy+=12)line(ctx,[[x+3,yy],[x+w-3,yy+2]],'#92978a',3);
    for(let xx=x+16;xx<x+w;xx+=57)line(ctx,[[xx,face+5],[xx-5,face+22],[xx+3,face+43]],'#485850',2);
    if(edgeOnly){line(ctx,[[x,y+h],[x,y],[x+w,y],[x+w,y+h]],'#dbcfaa',4);}
  }
  function drawSite(l,t){
    const{x,y}=l,remaining=me?.site_cooldowns?.[l.id]||0,color=remaining?'#969e8b':l.action==='ward'?'#cab1ef':l.action==='wind'?'#b9e5d5':'#e6cc84';
    ellipse(ctx,x,y+4,33,15,'#34453866');
    if(l.action==='cache'){
      block(ctx,x-26,y-19,52,34,'#654837');block(ctx,x-25,y-30,50,15,'#b58a4e');block(ctx,x-24,y-17,48,28,remaining?'#827652':'#9f7844');
      for(const dx of[-18,14]){block(ctx,x+dx,y-29,5,39,'#e2bd70');}block(ctx,x-5,y-9,10,12,'#e7c87b');block(ctx,x-1,y-6,3,6,'#504a38');
    }else if(l.action==='spring'){
      ellipse(ctx,x,y,36,23,'#c4c5a2');ellipse(ctx,x,y-2,27,16,'#5aa9b4');ellipse(ctx,x,y-3,18,9,'#9ddacc');line(ctx,[[x-10,y-4],[x+5,y-4]],'#d2f0dd',2);
    }else{block(ctx,x-19,y-10,38,19,'#7e8278');block(ctx,x-12,y-49,24,44,'#a7aa97');block(ctx,x-9,y-46,4,31,'#d4ceb3');label(l.action==='wind'?'≈':'◇',x,y-24,color,22);}
    if(!remaining)glow(x,y-15,34,color,.12+Math.sin(t*2)*.03);
    label(l.name,x,y-66,color,10);
    if(me&&distance(me,l)<105)label(remaining?`Odnowienie ${Math.ceil(remaining)} s`:'[E] '+({cache:'Otwórz skrytkę',spring:'Napij się',wind:'Wezwij wiatr',ward:'Przyjmij osłonę'}[l.action]),x,y+30,color,11);
  }
  function drawRiver(t){
    const r=world.river;if(!r||!inView(r.x+r.w/2,camera.y,r.w))return;
    block(ctx,r.x-12,0,r.w+24,r.h,"#b9bb77");block(ctx,r.x-6,0,r.w+12,r.h,"#62a890");block(ctx,r.x,0,r.w,r.h,"#449ead");block(ctx,r.x+16,0,r.w-32,r.h,"#438fa6");
    const y0=Math.max(0,Math.floor((camera.y-viewport.h/camera.scale/2-35)/32)*32),y1=Math.min(r.h,camera.y+viewport.h/camera.scale/2+35);
    for(let y=y0;y<y1;y+=32)for(let k=0;k<5;k++){const x=r.x+8+k*34+Math.sin(y*.063+k+t*.6)*6,yy=y+Math.sin(t*1.5+k+y)*3;line(ctx,[[x,yy],[x+8,yy],[x+12,yy-3],[x+20,yy-3]],"#a0d5c88c",2);}
    for(let y=y0;y<y1;y+=64){block(ctx,r.x-12,y,8,12,"#e0cf91");block(ctx,r.x+r.w+3,y+23,9,8,"#ddcb91");}
    const by=r.bridge_y??1080,bh=r.bridge_h??150;
    block(ctx,r.x-18,by,r.w+36,bh,"#685336");
    for(let y=by+5;y<by+bh-3;y+=12){block(ctx,r.x-18,y,r.w+36,10,y%24?"#bc9255":"#c49b61");line(ctx,[[r.x-12,y+2],[r.x+r.w+12,y+2]],"#e0b574",1);for(let x=r.x;x<r.x+r.w;x+=55)block(ctx,x,y+2,2,6,"#92713e");}
    for(const y of[by,by+bh-8]){block(ctx,r.x-22,y-6,r.w+44,8,"#795b35");block(ctx,r.x-22,y-8,r.w+44,3,"#d3ac70");for(let x=r.x-20;x<=r.x+r.w+20;x+=44){block(ctx,x,y-14,7,20,"#8c6b3f");block(ctx,x,y-14,7,4,"#e5be7e");}}
  }
  function drawSafeZone(){for(const z of world.safe_zones||[world.safe_zone]){if(!z||!sameFloor(me,z)||!inView(z.x,z.y,z.radius))continue;ctx.save();ctx.strokeStyle=me?.pvp_combat_remaining>0?"#eb8c57aa":"#d4e99778";ctx.lineWidth=2;ctx.setLineDash([5,11]);ctx.beginPath();ctx.arc(z.x,z.y,z.radius||260,0,TAU);ctx.stroke();ctx.restore();}}
  function fire(x,y,t,scale=1){
    ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);const flick=Math.sin(t*12+x)*3;
    ellipse(ctx,0,4,14,6,"#563d28");line(ctx,[[-11,3],[10,-1]],"#725236",5);line(ctx,[[10,3],[-10,-1]],"#9c6d39",4);
    glow(0,-6,38,"#ffc74c",.16);ctx.fillStyle="#e45e2c";ctx.beginPath();ctx.moveTo(-10,1);ctx.lineTo(-8,-12);ctx.lineTo(-3,-8);ctx.lineTo(1+flick,-27);ctx.lineTo(6,-15);ctx.lineTo(11,1);ctx.fill();
    ctx.fillStyle="#ffac39";ctx.beginPath();ctx.moveTo(-7,1);ctx.lineTo(-4,-13-flick);ctx.lineTo(0,-10);ctx.lineTo(3,-18);ctx.lineTo(7,1);ctx.fill();block(ctx,-2,-9,5,10,"#fff29b");ctx.restore();
  }
  function drawVillage(t){
    if(!inView(560,1180,270))return;
    // Open welcome square: banners, a communal fire, pots and low planters.
    fire(515,1228,t,.85);
    for(const [x,y]of[[368,1160],[787,1190]]){
      block(ctx,x,y-43,4,44,"#695034");block(ctx,x-2,y-47,8,5,"#d9b65e");block(ctx,x+4,y-40,17,26,"#b64238");block(ctx,x+5,y-40,14,2,"#f1c06b");block(ctx,x+10,y-33,5,10,"#e5c875");
    }
    for(const [x,y]of[[397,1200],[704,1090],[672,1284]]){block(ctx,x-8,y-3,16,9,"#a26846");block(ctx,x-11,y-6,22,5,"#d39461");block(ctx,x-7,y-17,14,11,"#508447");block(ctx,x-10,y-15,8,7,"#7fac48");block(ctx,x+5,y-12,7,6,"#6b9d46");block(ctx,x-4,y-18,4,5,"#eaa1c3");block(ctx,x+4,y-15,4,5,"#ffe3a0");}
    label("PRZYSTAŃ",560,1013,"#fff0b4",12);
  }
  function drawMerchant(t){
    const{x,y}=world.merchant;if(!inView(x,y))return;
    ellipse(ctx,x,y+7,29,10,"#34482d55");
    // The passable stall is open at the front, with its clerk behind the counter.
    humanoid(x,y-9,"merchant",[0,1],0,false);
    block(ctx,x-29,y-10,58,23,"#845c34");block(ctx,x-30,y-12,60,7,"#d2a86d");for(let k=0;k<5;k++)block(ctx,x-23+k*11,y-4,1,16,"#b08046");
    for(const dx of[-28,26]){block(ctx,x+dx,y-58,3,48,"#674c30");block(ctx,x+dx,y-57,2,7,"#c49b57");}
    block(ctx,x-32,y-63,64,15,"#e3bf74");for(let k=0;k<5;k++)block(ctx,x-30+k*13,y-63,7,15,"#b74738");block(ctx,x-34,y-50,68,5,"#f4d497");
    block(ctx,x-19,y-19,5,8,"#cc4d47");block(ctx,x-18,y-22,3,4,"#f5d5a0");block(ctx,x-4,y-17,5,6,"#59a1d9");block(ctx,x-3,y-20,3,4,"#f4d494");block(ctx,x+13,y-18,8,5,"#e5c754");
    label("Kupiec",x,y-80,"#ffe5a0",10);
  }
  function pixelTree(g,x,y,size=1,variant=0){
    g.save();g.translate(Math.round(x),Math.round(y));g.scale(size,size);
    block(g,-20,-2,43,14,"#3e643c55");block(g,-5,-32,10,36,"#62452b");block(g,-2,-31,4,34,"#987343");block(g,-10,1,19,5,"#775b32");
    const shades=variant===2?["#9c5a2c","#c08033","#dda742","#efc35e"]:variant===1?["#285d39","#397845","#52914b","#86b65d"]:["#3b7234","#4e913c","#70aa46","#a0c865"];
    const patches=[[-28,-51,56,22,0],[-21,-67,43,19,0],[-13,-76,28,12,0],[-33,-43,65,15,0],[-25,-63,40,23,1],[-30,-47,47,22,1],[-9,-59,36,26,1],[-16,-71,26,20,2],[-25,-55,28,20,2],[2,-47,25,14,2],[-11,-68,17,6,3],[-22,-52,11,5,3],[9,-43,10,4,3]];
    for(const[a,b,c,d,k]of patches)block(g,a,b,c,d,shades[k]);
    for(const[a,b]of[[-20,-41],[3,-59],[15,-30],[-7,-32]]){block(g,a,b,4,3,"#b2d27a88");}
    if(variant===0){block(g,-17,-35,4,4,"#d78545");block(g,10,-53,4,4,"#e4a551");}g.restore();
  }
  function drawHouse(o,index){
    const{x,y,w,h}=o;
    block(ctx,x+6,y+8,w,h,"#38563455");block(ctx,x,y+18,w,h-18,"#715e44");block(ctx,x+4,y+24,w-8,h-29,"#e1cb99");
    for(let xx=x+5;xx<x+w;xx+=27)block(ctx,xx,y+24,4,h-29,"#8e6845");block(ctx,x,y+h-9,w,9,"#9d9581");
    const roofColors=index%2?["#a46a32","#bf8740","#dbad5d"]:["#934638","#b5533e","#d7784b"];
    for(let row=0;row<5;row++){
      const yy=y-14+row*9,inset=Math.max(0,(2-row)*5);block(ctx,x-7+inset,yy,w+14-inset*2,10,roofColors[0]);
      for(let xx=x-5+inset+(row%2)*7;xx<x+w+5-inset;xx+=16){block(ctx,xx,yy+1,13,6,roofColors[1]);block(ctx,xx,yy+1,12,2,roofColors[2]);}
    }
    block(ctx,x-7,y+31,w+14,5,"#694b32");block(ctx,x+w*.44,y+h-35,22,27,"#675335");block(ctx,x+w*.44+3,y+h-32,15,24,"#8c6a3c");block(ctx,x+w*.44+14,y+h-22,3,3,"#e6c978");
    for(const xx of[x+13,x+w-27]){block(ctx,xx,y+h-37,15,17,"#765733");block(ctx,xx+2,y+h-35,11,11,"#739ea0");block(ctx,xx+6,y+h-35,2,12,"#dbc697");block(ctx,xx+1,y+h-21,15,3,"#b79459");}
    block(ctx,x+w-26,y-26,13,23,"#a39276");block(ctx,x+w-29,y-28,19,5,"#ccba93");
  }
  function drawObstacle(o,index){
    const{x,y,w,h}=o;if(!inView(x+w/2,y+h/2,Math.max(w,h)+90))return;
    if(o.type==='terrace'||o.type==='canyon'){drawCliff(o);return;}
    if(o.type==='mountain'){
      ellipse(ctx,x+w*.55,y+h*.7,w*.64,h*.5,'#34453855');
      const peaks=[[0,h],[w*.08,h*.18],[w*.33,-h*.65],[w*.54,h*.05],[w*.74,-h*.25],[w,h*.3],[w,h],[0,h]];
      ctx.fillStyle='#727d78';ctx.beginPath();peaks.forEach(([a,b],i)=>i?ctx.lineTo(x+a,y+b):ctx.moveTo(x+a,y+b));ctx.fill();
      ctx.fillStyle='#a5ac99';ctx.beginPath();ctx.moveTo(x+w*.08,y+h*.18);ctx.lineTo(x+w*.33,y-h*.65);ctx.lineTo(x+w*.41,y+h*.6);ctx.lineTo(x,y+h);ctx.fill();
      line(ctx,[[x+w*.33,y-h*.6],[x+w*.54,y+h*.08],[x+w*.7,y+h*.18]],'#d0cab0',3);
      for(let i=0;i<5;i++)line(ctx,[[x+w*.42,y+i*h*.18],[x+w*.88,y+i*h*.18+10]],'#535f5c',2);return;
    }
    if(o.type==="house"){drawHouse(o,index);return;}
    if(o.type==="mill"){
      block(ctx,x+5,y+3,w,h,"#455a3c55");block(ctx,x,y+12,w,h-12,"#a18d63");block(ctx,x+6,y+15,w-12,h-16,"#d0bc8d");
      for(let yy=y+20;yy<y+h;yy+=13)line(ctx,[[x+3,yy],[x+w-3,yy]],"#9d916d",2);
      ctx.fillStyle="#996537";ctx.beginPath();ctx.moveTo(x-6,y+15);ctx.lineTo(x+w/2,y-20);ctx.lineTo(x+w+6,y+15);ctx.fill();line(ctx,[[x-6,y+15],[x+w/2,y-20]],"#d8a562",3);
      const cx=x+w/2,cy=y+27;ctx.save();ctx.translate(cx,cy);ctx.rotate(-.15);
      for(let i=0;i<4;i++){ctx.rotate(Math.PI/2);block(ctx,0,-4,73,8,"#705433");block(ctx,27,-18,46,15,"#d9c58c");for(let j=30;j<73;j+=9)block(ctx,j,-17,2,13,"#967b4c");}ellipse(ctx,0,0,8,8,"#aa8050");ctx.restore();block(ctx,x+w/2-9,y+h-27,18,27,"#715b39");return;
    }
    if(o.type==="grove" || (x<1450 && y<2304 && !o.type)){
      block(ctx,x,y,w,h,"#4c763c");block(ctx,x+3,y+3,w-6,h-6,"#5f8a46");
      const cols=Math.max(2,Math.floor(w/50)),rows=Math.max(1,Math.floor(h/60));
      for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){const tx=x+(col+.5)*w/cols,ty=y+(row+1)*h/rows-4;pixelTree(ctx,tx,ty,Math.min(1.1,w/cols/43),(col+row+index)%3);}
    }else{
      block(ctx,x+5,y+8,w,h,"#3a4e4266");block(ctx,x,y,w,h,"#677a77");
      for(let row=0;row<h;row+=24)for(let col=0;col<w;col+=46){const ww=Math.min(43,w-col-2),hh=Math.min(21,h-row-2);if(ww>0&&hh>0){block(ctx,x+col+1,y+row+1,ww,hh,"#a0a899");block(ctx,x+col+2,y+row+2,ww-2,3,"#c6c7b0");block(ctx,x+col+2,y+row+hh-1,ww-2,2,"#829181");}}
      for(let k=0;k<w;k+=50)block(ctx,x+k,y-5,Math.min(23,w-k),10,"#c2c3ab");
      if(x>2200&&y>1400){for(let yy=y+40;yy<y+h;yy+=120){block(ctx,x+w*.45,yy,16,35,"#7a4b96");block(ctx,x+w*.45+6,yy+5,4,18,"#d4b367");}}
      else{block(ctx,x+7,y+h-9,Math.min(29,w-8),7,"#6e9a55");block(ctx,x+w-25,y+3,19,6,"#82a764");}
    }
  }
  function humanoid(x,y,kind,facing=[0,1],phase=0,dead=false){
    const info=classInfo[kind]||{cape:kind==="merchant"?"#c38b40":kind==="goblin"?"#aa6945":"#72836b",color:"#efcf87"};
    ctx.save();ctx.translate(Math.round(x),Math.round(y));if(facing[0]<-.3)ctx.scale(-1,1);if(dead){ctx.rotate(-Math.PI/2);ctx.globalAlpha=.65;}
    const bob=Math.round(Math.sin(phase*8)),step=Math.round(Math.sin(phase*9)*2),cape=info.cape;
    block(ctx,-9,-1+step,7,7,"#4b3930");block(ctx,3,-1-step,7,7,"#4b3930");block(ctx,-9,4+step,9,3,"#302f2b");block(ctx,3,4-step,9,3,"#302f2b");
    block(ctx,-12,-25+bob,24,26,"#364536");block(ctx,-10,-25+bob,20,27,cape);block(ctx,-10,-24+bob,4,24,"#ffffff20");block(ctx,8,-22+bob,4,23,"#00000024");
    if(kind==="knight"){
      block(ctx,-9,-25+bob,19,19,"#c1c6bb");block(ctx,-7,-23+bob,6,13,"#edf0d5");block(ctx,2,-23+bob,6,13,"#929f9d");block(ctx,-13,-25+bob,8,7,"#dce1cb");block(ctx,8,-25+bob,7,7,"#8f9e98");block(ctx,-9,-8+bob,19,4,"#ac844c");block(ctx,-2,-8+bob,5,4,"#e2c971");
      block(ctx,-15,-17+bob,8,16,"#623d34");block(ctx,-14,-15+bob,6,11,"#b6473c");block(ctx,-12,-14+bob,2,9,"#eac36c");
    }else if(kind==="paladin"){
      block(ctx,-8,-23+bob,16,16,"#987045");block(ctx,-5,-23+bob,10,4,"#d3ad63");block(ctx,-8,-9+bob,17,4,"#574a2f");block(ctx,-2,-9+bob,4,4,"#dbb768");line(ctx,[[-7,-22+bob],[7,-9+bob]],"#d6b270",3);
    }else{block(ctx,-7,-24+bob,14,19,cape);block(ctx,-8,-7+bob,17,3,"#dcc079");block(ctx,-1,-24+bob,3,16,info.color);block(ctx,-8,-1+bob,18,3,info.color);}
    block(ctx,-16,-21+bob,5,13,cape);block(ctx,11,-21+bob,5,13,cape);block(ctx,-16,-9+bob,5,5,"#e5b57e");block(ctx,12,-9+bob,5,5,"#e5b57e");
    block(ctx,-7,-38+bob,14,15,"#65442e");block(ctx,-6,-36+bob,12,12,"#e0ab75");block(ctx,-4,-35+bob,8,9,"#f3c993");block(ctx,-4,-35+bob,2,4,"#faddaa");
    if(facing[1]<-.3){block(ctx,-7,-37+bob,14,12,kind==="knight"?"#b5c1b5":"#73512f");}
    else{block(ctx,-3,-30+bob,2,2,"#3b4134");block(ctx,3,-30+bob,2,2,"#3b4134");block(ctx,-1,-26+bob,4,2,"#a96d4c");}
    if(kind==="knight"){block(ctx,-9,-40+bob,18,8,"#9facaa");block(ctx,-6,-43+bob,12,5,"#ccd2c0");block(ctx,-8,-40+bob,5,5,"#e3e5d0");block(ctx,-1,-44+bob,4,6,"#d44d3e");}
    else if(kind==="mage"){block(ctx,-10,-38+bob,21,4,"#2f438b");block(ctx,-7,-44+bob,15,8,"#587cc9");block(ctx,-3,-49+bob,7,8,"#6f91dc");block(ctx,-2,-53+bob,4,6,"#a6b8eb");block(ctx,-7,-39+bob,15,3,"#dabf72");}
    else if(kind==="druid"){block(ctx,-8,-40+bob,17,7,"#467844");block(ctx,-5,-43+bob,12,6,"#80a451");block(ctx,-9,-37+bob,3,12,"#517e44");block(ctx,6,-37+bob,3,12,"#517e44");}
    else{block(ctx,-8,-40+bob,17,6,"#9d713e");block(ctx,-6,-43+bob,12,5,"#bd9355");block(ctx,-10,-38+bob,21,3,"#735736");}
    if(kind==="knight"){block(ctx,18,-27+bob,3,22,"#d7e6db");block(ctx,18,-31+bob,2,5,"#f1f4d9");block(ctx,14,-8+bob,11,3,"#dbb964");block(ctx,18,-4+bob,3,7,"#77542e");}
    else if(kind==="paladin"){line(ctx,[[19,-31+bob],[24,-24+bob],[27,-14+bob],[23,-4+bob],[19,2+bob]],"#d3ad66",3);line(ctx,[[19,-31+bob],[19,2+bob]],"#ede4b8",1);}
    else if(kind!=="merchant"){block(ctx,19,-35+bob,3,39,"#8b6136");block(ctx,17,-40+bob,7,8,kind==="mage"?"#80bbfa":"#b7e481");block(ctx,19,-39+bob,3,4,"#eef7b9");}
    ctx.restore();
  }
  function drawNPC(npc,t){
    if(!inView(npc.x,npc.y))return;
    ellipse(ctx,npc.x,npc.y+6,16,7,"#35452d66");
    const type=npc.id==="strazniczka"?"knight":npc.id==="kartograf"?"mage":"paladin";
    humanoid(npc.x,npc.y,type,[0,1],0,false);
    const quests=(me?.quests||[]).filter(q=>q.npc_id===npc.id),ready=quests.some(q=>q.status==="ready"),available=quests.some(q=>q.status==="available"),active=quests.some(q=>q.status==="active");
    if(ready||available||active){const y=npc.y-72+Math.sin(t*3)*2;label(ready?"?":available?"!":"•",npc.x,y,ready?"#c8f889":available?"#fff29e":"#d3d8c1",21);}
    label(npc.name,npc.x,npc.y-55,"#f9e396",10);
  }
  function drawLandmark(l,t){
    if(l.id.startsWith('habitat_'))return;
    const{x,y}=l;if(!inView(x,y,130))return;const found=(me?.discoveries||[]).includes(l.id);
    if(l.action){drawSite(l,t);return;}
    if(l.decoration==='sign'){
      block(ctx,x-3,y-57,6,62,'#77573a');block(ctx,x-43,y-57,86,17,'#c4a26c');block(ctx,x-34,y-35,69,16,'#b7955f');label('SZLAKI · K → Atlas',x,y-44,'#443b2c',9);
    }else if(l.id==="old_mill"){
      // Mill yard: sacks, cut wheat and a broken cart alongside the solid mill tower.
      for(const[dx,dy]of[[-22,8],[5,18],[25,7]]){block(ctx,x+dx-9,y+dy-12,18,19,"#af9460");block(ctx,x+dx-7,y+dy-14,14,6,"#dac185");block(ctx,x+dx-5,y+dy-6,3,9,"#cab078");}
      line(ctx,[[x-67,y+22],[x-43,y+23]],"#956837",10);for(const dx of[-62,-47]){ellipse(ctx,x+dx,y+29,8,8,"#66502f");ellipse(ctx,x+dx,y+29,4,4,"#c0a366");}
    }else if(l.id==="goblin_camp"){
      fire(x,y+7,t,1.3);for(let k=0;k<3;k++){const dx=(k-1)*55;block(ctx,x+dx-13,y+54,29,15,"#856640");block(ctx,x+dx-11,y+55,25,8,"#c09c60");}
      for(const dx of[-70,66]){block(ctx,x+dx,y-43,5,47,"#805335");block(ctx,x+dx-5,y-45,17,11,"#ded3a5");block(ctx,x+dx-2,y-41,3,3,"#765a3b");block(ctx,x+dx+5,y-41,3,3,"#765a3b");}
    }else if(l.id==="marsh_shrine"){
      for(let i=0;i<8;i++){const a=i/8*TAU;block(ctx,x+Math.cos(a)*33-7,y+Math.sin(a)*23-5,14,10,"#c4c5a2");block(ctx,x+Math.cos(a)*33-5,y+Math.sin(a)*23-5,9,3,"#e0d8ac");}
      ellipse(ctx,x,y,21,13,"#67bab9");ellipse(ctx,x,y-2,13,7,"#a6e8ce");for(let i=0;i<5;i++){const a=t+i*1.25,xx=x+Math.cos(a)*37,yy=y-20+Math.sin(a*1.2)*19;glow(xx,yy,12,"#a7e9d5",.3);block(ctx,xx,yy,3,3,"#eafcb1");}
    }else if(l.id==="dawn_ruins"){
      for(let i=0;i<4;i++){const dx=(i-1.5)*25;block(ctx,x+dx-10,y-5+Math.abs(i-1.5)*12,23,17,"#a8a791");block(ctx,x+dx-8,y-5+Math.abs(i-1.5)*12,19,4,"#d5c9a1");}
      ctx.save();ctx.strokeStyle="#b2a277";ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(x,y-17,41,25,0,0,TAU);ctx.stroke();ctx.restore();
    }else if(l.id==="fortress"){
      for(const dx of[-69,68]){block(ctx,x+dx,y-40,5,48,"#755448");block(ctx,x+dx+5,y-38,20,29,"#77489b");block(ctx,x+dx+12,y-31,5,15,"#e3c981");fire(x+dx+2,y-43,t,.45);}
    }else if(l.id==="old_bridge"){
      block(ctx,x+18,y-30,4,38,"#825f38");block(ctx,x+3,y-35,36,15,"#cba265");line(ctx,[[x+10,y-28],[x+29,y-28]],"#775939",2);
    }
    if(l.id.startsWith('land_')||l.id.startsWith('wild_')){for(let i=0;i<6;i++){const a=i/6*TAU;block(ctx,x+Math.cos(a)*37-5,y+Math.sin(a)*22-9,10,19,'#9e9d88');block(ctx,x+Math.cos(a)*37-4,y+Math.sin(a)*22-10,8,4,'#d2c7a0');}if(l.id.startsWith('land_'))fire(x,y,t,.6);}
    const near=me&&distance(me,l)<190;
    if(near||!playing)label(`${found?"✓ ":"◇ "}${l.name}`,x,y-92,found?"#e3edb8":"#fff0bd",11);
  }
  function drawPlayer(v,t){
    const p=v.entity,x=v.x,y=v.y,isMe=String(p.id)===myId;if(!inView(x,y))return;
    if(String(p.id)===selectedTarget){ctx.strokeStyle="#f05942";ctx.lineWidth=2;ctx.strokeRect(x-20,y-44,40,50);}
    if(isMe){ctx.strokeStyle="#e5eeae88";ctx.lineWidth=1.5;ctx.strokeRect(x-16,y-14,32,28);}
    ellipse(ctx,x,y+6,17,7,"#2c422e70");humanoid(x,y,p.class_id,p.facing||[0,1],v.move,p.hp<=0);
    const color=p.skull==="red"?"#ff9b83":p.skull==="white"?"#fff6dc":isMe?"#fff2a8":me?.party_id&&p.party_id===me.party_id?"#a1eff2":"#c3f4a9";
    label(`${p.skull&&p.skull!=="none"?"☠ ":""}${p.name}${p.disconnected?" · offline":""}`,x,y-66,color,11);
    block(ctx,x-18,y-55,36,4,"#304232");block(ctx,x-17,y-54,34*Math.max(0,p.hp/p.max_hp),2,isMe?"#86df6b":"#9fd672");
  }
  function drawEnemy(v,t){
    if(String(v.entity.id)===selectedEnemy){const z=v.entity.size||1;ctx.strokeStyle='#f05942';ctx.lineWidth=2;ctx.strokeRect(v.x-30*z,v.y-62*z,60*z,70*z);}
    const e=v.entity,x=v.x,y=v.y,spec=world.enemy_types?.[e.kind]||{},kind=spec.appearance||e.kind;if(["bear","harpy","cyclops","ghoul","scorpion"].includes(kind)){drawWildCreature(v,t,spec);return;}if(["dragon","demon"].includes(kind)){drawNewCreature(v,t,spec);return;}if(!inView(x,y)||e.alive===false||e.hp<=0)return;
    const phase=Math.round(Math.sin(v.move*8)*2),flip=(e.facing?.[0]||1)<0?-1:1;
    ellipse(ctx,x,y+6,kind==="boss"?34:kind==="rat"?11:20,kind==="boss"?13:7,"#3143316b");ctx.save();ctx.translate(Math.round(x),Math.round(y));ctx.scale(flip*(spec.size||1),spec.size||1);
    if(kind==="wolf"||kind==="boar"||kind==="rat"){
      const rat=kind==="rat",boar=kind==="boar",s=rat?.7:boar?1.1:1;ctx.scale(s,s);
      const dark=rat?"#796355":boar?"#715038":"#667786",body=spec.color||(rat?"#b5987b":boar?"#a37545":"#adbfc0"),light=rat?"#d0b293":boar?"#c39760":"#d5ded0";
      for(const dx of[-12,10]){block(ctx,dx,-1+(dx<0?phase:-phase),5,9,dark);block(ctx,dx+2,6+(dx<0?phase:-phase),6,3,dark);}
      block(ctx,-20,-19,36,20,dark);block(ctx,-18,-22,31,19,body);block(ctx,-16,-21,24,5,light);block(ctx,12,-27,18,18,body);block(ctx,24,-17,12,8,light);block(ctx,33,-17,4,5,dark);
      block(ctx,15,-33,5,11,dark);block(ctx,24,-32,5,8,dark);block(ctx,23,-24,3,3,rat?"#bd523c":"#f2df82");
      if(rat){line(ctx,[[-19,-10],[-30,-16],[-39,-10]],"#c6a48b",3);block(ctx,15,-31,4,6,"#d99d8b");}
      else if(boar){block(ctx,29,-9,4,8,"#eee2bc");block(ctx,32,-14,4,5,"#fff0c2");for(let k=0;k<5;k++)block(ctx,-14+k*6,-25,3,8,dark);}
      else{line(ctx,[[-17,-10],[-26,-14],[-31,-26]],body,6);block(ctx,-30,-30,5,8,light);}
    }else if(kind==="spider"){
      for(let i=0;i<4;i++){const yy=-18+i*8;for(const side of[-1,1])line(ctx,[[side*7,yy],[side*(21+i%2*3),yy-7+phase],[side*(29+i%2*2),yy+5+phase]],"#533e3c",3);}
      block(ctx,-12,-23,25,22,"#704b62");block(ctx,-9,-27,18,10,"#a7718a");block(ctx,-6,-24,4,6,"#d59a99");block(ctx,-8,-2,16,9,"#815564");for(const dx of[-5,2])block(ctx,dx,0,3,3,"#f5d874");
    }else if(kind==="goblin"||kind==="skeleton"){
      const sk=kind==="skeleton",human=["bandit","bandit_archer","elf","vampire"].includes(e.kind),skin=spec.color||(sk?"#d8d0ae":"#83b557"),shadow=sk?"#a7a78a":"#537f44";
      block(ctx,-10,-4+phase,6,12,shadow);block(ctx,6,-4-phase,6,12,shadow);block(ctx,-10,5+phase,8,4,"#5b4d36");block(ctx,6,5-phase,8,4,"#5b4d36");
      block(ctx,-11,-24,22,24,sk?skin:"#996b40");block(ctx,-8,-21,16,12,skin);if(sk)for(let j=0;j<3;j++)block(ctx,-8,-19+j*4,16,2,"#817f66");else{block(ctx,-11,-9,22,7,"#986642");block(ctx,-1,-8,4,4,"#d8b46c");}
      block(ctx,-16,-20,5,17,shadow);block(ctx,12,-20,5,17,skin);block(ctx,-10,-43,21,18,shadow);block(ctx,-8,-44,17,18,skin);block(ctx,-6,-42,8,5,sk?"#ebe2bd":"#b4d278");
      if(!sk){if(!human){block(ctx,-15,-40,8,6,skin);block(ctx,8,-40,8,6,skin);}block(ctx,-8,-47,18,5,"#b27141");}
      for(const dx of[-5,3])block(ctx,dx,-35,4,4,sk?"#555647":"#594329");block(ctx,-3,-28,9,3,sk?"#76775e":"#d9db9f");
      block(ctx,20,-27,3,29,"#786141");block(ctx,20,-30,7,12,sk?"#c2d1c4":"#aeb59a");block(ctx,-19,-10,7,13,"#8c633e");
    }else if(kind==="wisp"){
      const bob=Math.sin(t*3+x)*4;glow(0,-20+bob,39,"#9cdeea",.34);block(ctx,-9,-29+bob,18,22,"#6fc5d0aa");block(ctx,-5,-32+bob,10,21,"#c0f3e1");block(ctx,-2,-30+bob,5,15,"#f0ffd3");block(ctx,-7,-10+bob,5,10,"#84d4b7");block(ctx,-10,0+bob,4,6,"#a5e3bf");
    }else{
      const boss=kind==="boss"||spec.boss;
      block(ctx,-14,-2+phase,10,14,"#566d6a");block(ctx,5,-2-phase,10,14,"#566d6a");block(ctx,-17,-36,35,37,"#728c86");block(ctx,-13,-34,13,24,"#bbc4aa");block(ctx,1,-33,12,26,boss?"#8278a0":"#97a992");
      block(ctx,-23,-36,12,15,"#adb9a2");block(ctx,13,-36,12,15,"#93a68e");block(ctx,-11,-57,24,22,"#758b82");block(ctx,-9,-57,17,7,"#c8ccb1");block(ctx,-7,-46,15,4,"#394b48");block(ctx,-5,-46,4,3,boss?"#ffc957":"#c5f0b5");block(ctx,3,-46,4,3,boss?"#ffc957":"#c5f0b5");
      block(ctx,-2,-25,6,11,boss?"#e6bb61":"#bfe599");line(ctx,[[-7,-55],[-17,-65],[-17,-73]],"#b6b995",5);line(ctx,[[9,-55],[19,-66],[19,-73]],"#b6b995",5);
      if(boss){block(ctx,-14,-31,4,24,"#b8a1c5");glow(0,-20,31,"#dd8af1",.16);}
    }
    if(spec.projectile==='arrow'){line(ctx,[[21,-39],[31,-23],[21,-5]],'#d8b56d',3);line(ctx,[[21,-39],[21,-5]],'#eee1b7',1);}
    ctx.restore();
    const attackAge=(performance.now()-v.attackAt)/1000;
    if(attackAge>=0&&attackAge<.25){const angle=Math.atan2(e.facing?.[1]??1,e.facing?.[0]??0);ctx.save();ctx.translate(x,y-8);ctx.rotate(angle);ctx.globalAlpha=1-attackAge/.25;ctx.strokeStyle="#ffb36c";ctx.lineWidth=3;ctx.beginPath();ctx.arc(0,0,kind==="boss"?55:29,-.8+attackAge*3,.7+attackAge*3);ctx.stroke();ctx.restore();}
    const yoff=kind==="boss"?135:kind==="guardian"?91:kind==="goblin"||kind==="skeleton"?60:49,width=kind==="boss"?76:36;
    label(e.name||kind,x,y-yoff*(spec.size||1),"#fff0cc",kind==="boss"?12:9);block(ctx,x-width/2,y-yoff*(spec.size||1)+10,width,4,"#4d4d37");block(ctx,x-width/2+1,y-yoff*(spec.size||1)+11,(width-2)*Math.max(0,e.hp/e.max_hp),2,"#e87955");
  }
  function drawWildCreature(v,t,spec){
    const e=v.entity,x=v.x,y=v.y,z=spec.size||1,k=spec.appearance,col=spec.color||'#9d967a',step=Math.round(Math.sin(v.move*7)*2);
    if(e.hp<=0||!inView(x,y))return;
    ctx.save();ctx.translate(x,y);ctx.scale(z*((e.facing?.[0]||1)<0?-1:1),z);ellipse(ctx,0,5,26,9,'#263b3266');
    if(k==='bear'){
      block(ctx,-24,-30,43,29,'#664e3d');block(ctx,-22,-35,38,25,col);block(ctx,-18,-33,18,6,'#b48c64');block(ctx,9,-37,24,25,col);block(ctx,13,-42,6,8,'#76573f');block(ctx,27,-41,6,7,'#76573f');block(ctx,24,-23,15,8,'#c2a27b');block(ctx,35,-23,5,5,'#382f2a');block(ctx,26,-31,3,3,'#292b27');for(const dx of[-19,10]){block(ctx,dx,-3,9,12+step,'#614938');block(ctx,dx+2,7+step,10,3,'#e2d0a5');}
    }else if(k==='harpy'){
      for(const side of[-1,1]){ctx.fillStyle='#797e89';ctx.beginPath();ctx.moveTo(side*6,-27);ctx.lineTo(side*46,-54+Math.sin(t*6)*7);ctx.lineTo(side*34,-12);ctx.lineTo(side*8,-4);ctx.fill();for(let i=0;i<4;i++)line(ctx,[[side*(17+i*6),-18],[side*(22+i*6),-39]],'#c8c3b3',2);}block(ctx,-9,-34,19,31,col);block(ctx,-8,-49,18,17,'#d7b598');block(ctx,-12,-53,25,9,'#656d7d');block(ctx,5,-40,10,4,'#dbc57e');for(const dx of[-7,6]){line(ctx,[[dx,-4],[dx,9],[dx+8,11]],'#c6ac71',3);}
    }else if(k==='scorpion'){
      for(const side of[-1,1])for(let i=0;i<3;i++)line(ctx,[[side*9,-13+i*6],[side*24,-19+i*8],[side*30,-8+i*7]],'#86613b',3);
      block(ctx,-13,-24,27,25,col);for(let i=0;i<4;i++)block(ctx,-11,-22+i*6,23,2,'#a67c49');line(ctx,[[0,-23],[-13,-41],[-10,-58],[3,-64],[13,-56]],col,7);block(ctx,9,-57,5,11,'#594235');for(const side of[-1,1]){line(ctx,[[side*9,1],[side*22,10],[side*30,2]],col,6);block(ctx,side*30-3,-1,6,9,'#ead094');}
    }else{
      const giant=k==='cyclops';block(ctx,-12,-6+step,9,15,'#665441');block(ctx,5,-6-step,9,15,'#665441');block(ctx,-18,-36,36,34,col);block(ctx,-14,-33,14,21,'#c2b08a');block(ctx,-22,-32,8,27,col);block(ctx,16,-32,8,25,col);block(ctx,-13,-59,27,24,col);
      if(giant){if(e.kind==='ogre'){block(ctx,-7,-49,4,4,'#e9cb7e');block(ctx,4,-49,4,4,'#e9cb7e');}else{block(ctx,-7,-50,16,7,'#f2e3bc');block(ctx,-1,-50,4,6,'#43352a');}block(ctx,-8,-40,16,3,'#574333');line(ctx,[[24,-5],[30,-47]],'#765333',6);block(ctx,22,-54,18,18,'#a18456');}
      else{block(ctx,-18,-25,36,14,'#786673');block(ctx,-7,-48,4,4,'#e8c35d');block(ctx,5,-48,4,4,'#e8c35d');block(ctx,-6,-39,14,4,'#574c46');for(const side of[-1,1])for(let j=0;j<3;j++)block(ctx,side*23+j*2,-8,1,8,'#ddd0a6');}
    }
    ctx.restore();const yy=y-(k==='bear'||k==='scorpion'?75:82)*z;label(e.name,x,yy,'#efdfbd',10);block(ctx,x-23,yy+8,46,5,'#4d4939');block(ctx,x-22,yy+9,44*e.hp/e.max_hp,3,'#e87955');
  }
  function drawEffects(now){
    for(const[id,e]of effects){
      if(me&&!sameFloor(me,e)){effects.delete(id);continue;}
      const duration=e.duration||.32,age=(now-e.started)/1000,q=Math.max(0,Math.min(1,age/duration));if(age>duration){effects.delete(id);continue;}
      const x=e.x,y=e.y-17,tx=e.target_x??e.x,ty=(e.target_y??e.y)-17,angle=Math.atan2(ty-y,tx-x);
      ctx.save();
      const enemyColor=({stone:'#d5bf8a',arrow:'#f5d48d',venom:'#b4dd68',fire:'#ff9856',ice:'#9ae1f6',shadow:'#ce9ee7',arcane:'#9ccaf2',feather:'#e3d9bd'})[e.element||e.kind.replace('enemy_','')]||'#efbd8c';
      if(e.kind==='danger_zone'){
        ctx.fillStyle=e.special?'#ee755322':'#e0b0631c';ctx.beginPath();ctx.arc(tx,e.target_y,e.radius,0,TAU);ctx.fill();ctx.strokeStyle=enemyColor;ctx.lineWidth=e.special?3:2;ctx.setLineDash([8,6]);ctx.stroke();ctx.setLineDash([]);ctx.strokeStyle='#fff1c9';ctx.beginPath();ctx.arc(tx,e.target_y,Math.max(2,e.radius*q),-Math.PI/2,-Math.PI/2+TAU*q);ctx.stroke();if(e.special)label('UNIK!',tx,e.target_y-6,'#ffe4b2',11);
      }else if(e.kind==='enemy_impact'){
        ctx.globalAlpha=1-q;ctx.strokeStyle=enemyColor;ctx.lineWidth=4;ctx.beginPath();ctx.arc(x,e.y,e.radius*(.3+.7*q),0,TAU);ctx.stroke();for(let i=0;i<10;i++){const a=i/10*TAU;block(ctx,x+Math.cos(a)*e.radius*q,e.y+Math.sin(a)*e.radius*q-8,5,8,enemyColor);}
      }else if(e.kind.startsWith('enemy_')){
        const px=x+(tx-x)*q,py=y+(ty-y)*q-Math.sin(q*Math.PI)*(e.kind==='enemy_stone'?65:0);line(ctx,[[x+(tx-x)*Math.max(0,q-.13),y+(ty-y)*Math.max(0,q-.13)],[px,py]],enemyColor+'99',3);ctx.translate(px,py);ctx.rotate(angle);
        if(e.kind==='enemy_arrow'||e.kind==='enemy_feather'){line(ctx,[[-16,0],[13,0]],enemyColor,2);line(ctx,[[7,-4],[13,0],[7,4]],'#fff0cc',2);}else if(e.kind==='enemy_stone'){block(ctx,-8,-7,17,15,'#8f9283');block(ctx,-7,-7,12,5,'#d3c8a5');}else{glow(0,0,24,enemyColor,.55);block(ctx,-6,-5,13,11,enemyColor);block(ctx,-2,-3,5,5,'#fff3d5');}
      }else if(["magic_bolt","nature_bolt","arrow","piercing_arrow"].includes(e.kind)){
        const px=x+(tx-x)*q,py=y+(ty-y)*q,tail=Math.max(0,q-.22),color=e.kind==="nature_bolt"?"#b9f575":e.kind==="magic_bolt"?"#83c6ff":"#fbe4a8";
        line(ctx,[[x+(tx-x)*tail,y+(ty-y)*tail],[px,py]],color+"99",e.kind==="piercing_arrow"?7:3);
        ctx.translate(px,py);ctx.rotate(angle);
        if(e.kind.includes("arrow")){block(ctx,-13,-1,22,2,"#efe3ae");line(ctx,[[7,-4],[13,0],[7,4]],"#f8f2d2",2);line(ctx,[[-10,-3],[-6,0],[-10,3]],"#ce9967",2);}
        else{glow(0,0,20,color,.6);block(ctx,-7,-4,13,8,color);block(ctx,-3,-6,7,12,color);block(ctx,-2,-3,7,6,"#f6ffdf");}
      }else if(["fire_ring","ice_ring","haste"].includes(e.kind)){
        const radius=(e.radius||320)*(.25+.75*q),fade=Math.sin(Math.PI*Math.min(.99,q))* .75;
        ctx.globalAlpha=fade;ctx.strokeStyle=e.kind==="ice_ring"?"#99e1fa":e.kind==="haste"?"#d7f7b4":"#ffac40";ctx.lineWidth=5+5*(1-q);ctx.beginPath();ctx.ellipse(x,e.y,radius,radius,0,0,TAU);ctx.stroke();ctx.strokeStyle="#ffe1a0";ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(x,e.y,radius-8,radius-8,0,0,TAU);ctx.stroke();
        for(let k=0;k<28;k++){const a=k/28*TAU+q*.12,xx=x+Math.cos(a)*radius,yy=e.y+Math.sin(a)*radius;if(e.kind==="fire_ring")fire(xx,yy,now/1000+k,.7+.35*Math.sin(k+q*10));else block(ctx,xx,yy,5,9,e.kind==="ice_ring"?"#cef5ff":"#e1f6ba");}
        glow(x,y,Math.max(45,radius),"#ff9a32",.1*(1-q));
      }else if(e.kind==="sword"){
        ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha=1-q;ctx.strokeStyle="#fff4ba";ctx.lineWidth=7*(1-q)+1;ctx.beginPath();ctx.arc(0,0,43,-1.1+q,.35+q);ctx.stroke();ctx.strokeStyle="#cfe5e3";ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,50,-1+q,.4+q);ctx.stroke();
      }else if(e.kind==="heal"){
        const hx=e.target_x??e.x,hy=e.target_y??e.y,radius=e.radius||80;ctx.globalAlpha=1-q;ctx.strokeStyle="#b3ef92";ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(hx,hy,radius*q,radius*q*.6,0,0,TAU);ctx.stroke();
        for(let k=0;k<8;k++){const a=k/8*TAU,xx=hx+Math.cos(a)*40,yy=hy-17+Math.sin(a)*25-q*50;block(ctx,xx-2,yy-7,4,14,"#d1ffa3");block(ctx,xx-7,yy-2,14,4,"#d1ffa3");}
      }else if(e.kind==="bulwark"){
        ctx.globalAlpha=1-q;ctx.strokeStyle="#fce18b";ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(x-27,y-29);ctx.lineTo(x,y-40);ctx.lineTo(x+27,y-29);ctx.lineTo(x+21,y+8);ctx.lineTo(x,y+27);ctx.lineTo(x-21,y+8);ctx.closePath();ctx.stroke();glow(x,y,65,"#ffd86c",.25);
      }
      ctx.restore();
    }
  }
  function drawSpeech(v,now){
    const p=v.entity,serverTime=Number(snapshot.time||0)+Math.min(.5,(now-lastSnapshotAt)/1000);
    if(!p.speech_text||Number(p.speech_until)<=serverTime||!inView(v.x,v.y))return;
    const words=String(p.speech_text).split(/\s+/),lines=[];let row="";ctx.font="600 11px system-ui,sans-serif";
    for(const word of words){
      const chunks=word.match(/.{1,25}/gu)||[word];
      for(const chunk of chunks){const candidate=row?`${row} ${chunk}`:chunk;if(ctx.measureText(candidate).width>185&&row){lines.push(row);row=chunk;}else row=candidate;}
    }
    if(row)lines.push(row);const height=lines.length*15+10,width=Math.min(210,Math.max(35,...lines.map(l=>ctx.measureText(l).width))+16),x=v.x-width/2,y=v.y-88-height;
    rounded(ctx,x,y,width,height,4,"#283225d9");ctx.strokeStyle="#e9d797a0";ctx.lineWidth=1;ctx.strokeRect(Math.round(x)+.5,Math.round(y)+.5,Math.round(width),height);ctx.fillStyle="#283225d9";ctx.beginPath();ctx.moveTo(v.x-5,y+height);ctx.lineTo(v.x,y+height+6);ctx.lineTo(v.x+5,y+height);ctx.fill();
    lines.forEach((text,i)=>label(text,v.x,y+13+i*15,"#fff09b",11));
  }
  function addParticles(x,y,color,count){for(let i=0;i<count;i++)particles.push({x,y,vx:(Math.random()-.5)*70,vy:-25-Math.random()*60,life:.35+Math.random()*.25,color});}
  function drawParticles(dt){for(let i=particles.length-1;i>=0;i--){const p=particles[i];p.life-=dt;if(p.life<=0){particles.splice(i,1);continue;}p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=90*dt;ctx.globalAlpha=Math.min(1,p.life*3);block(ctx,p.x,p.y,3,3,p.color);}ctx.globalAlpha=1;for(let i=floatingTexts.length-1;i>=0;i--){const p=floatingTexts[i];p.life-=dt;if(p.life<=0){floatingTexts.splice(i,1);continue;}p.y-=25*dt;ctx.globalAlpha=Math.min(1,p.life*2);label(p.text,p.x,p.y,p.color,14);}ctx.globalAlpha=1;}
  function drawGoal(){
    if(!me||!activeGoal||!sameFloor(me,activeGoal)||!ui.sidePanel.hidden)return;
    const target=activeGoal,d=distance(me,target);if(d<75)return;
    const angle=Math.atan2(target.y-me.y,target.x-me.x),radius=Math.min(102,Math.max(68,d*.35)),x=me.x+Math.cos(angle)*radius,y=me.y+Math.sin(angle)*radius;
    ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.globalAlpha=.82;ctx.fillStyle="#ffdf80";ctx.strokeStyle="#665638";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(9,0);ctx.lineTo(-7,-6);ctx.lineTo(-4,0);ctx.lineTo(-7,6);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
  }
  function drawMinimap(){
    if(ui.minimapCard.hidden||!playing||!me)return;
    const viewKey=`${viewport.w}:${viewport.h}:${camera.scale}`;
    if(minimapSnapshot===snapshot&&minimapViewport===viewKey)return;
    minimapSnapshot=snapshot;minimapViewport=viewKey;
    const w=mini.width,h=mini.height,mw=4800,mh=3400,left=me.x-mw/2,top=me.y-mh/2,sx=w/mw,sy=h/mh;
    mctx.fillStyle=me.floor?'#302e38':'#456447';mctx.fillRect(0,0,w,h);
    for(const r of world.regions||[]){mctx.fillStyle=r.color;mctx.fillRect((r.x-left)*sx,(r.y-top)*sy,r.w*sx,r.h*sy);}
    if(me.floor){if(me.floor<0){mctx.fillStyle='#252831';mctx.fillRect(0,0,w,h);}for(const d of [...(world.dungeons||[]),...(world.elevations||[])])if(d.floor===me.floor)for(const r of d.rooms){mctx.fillStyle='#a1937a';mctx.fillRect((r.x-left)*sx,(r.y-top)*sy,r.w*sx,r.h*sy);}}
    else for(const edge of surfaceMap?.roads(left,top,left+mw,top+mh)||[])line(mctx,[edge.a,edge.b].map(([x,y])=>[(x-left)*sx,(y-top)*sy]),'#d5bd85',2);
    if(!me.floor)for(const entry of staticIndex.query(left,top,left+mw,top+mh,0)){const r=entry.data;if(entry.kind==='waterway'||entry.kind==='bridge')line(mctx,[r.a,r.b].map(([x,y])=>[(x-left)*sx,(y-top)*sy]),entry.kind==='bridge'?'#e3c388':'#559ebc',entry.kind==='bridge'?2:Math.max(2,r.width*sx));}
    for(const l of world.landmarks||[])if(l.hint&&sameFloor(me,l)){mctx.fillStyle='#f6dfa6';mctx.fillRect((l.x-left)*sx-2,(l.y-top)*sy-2,4,4);}
    for(const c of world.cities||[])if(sameFloor(me,c))ellipse(mctx,(c.x-left)*sx,(c.y-top)*sy,6,6,'#eac879');
    for(const stair of world.stairs||[])if(sameFloor(me,stair)){mctx.fillStyle='#e1bbff';mctx.fillRect((stair.x-left)*sx-2,(stair.y-top)*sy-2,4,4);}
    for(const e of snapshot.enemies||[])if(e.alive)ellipse(mctx,(e.x-left)*sx,(e.y-top)*sy,1.5,1.5,'#f5a16e');
    for(const p of snapshot.players)if(sameFloor(me,p))ellipse(mctx,(p.x-left)*sx,(p.y-top)*sy,p.id===myId?3:2,p.id===myId?3:2,p.id===myId?'#fff':'#93d5e3');
    mctx.strokeStyle='#f9e4b8';mctx.strokeRect(w/2-viewport.w/camera.scale*sx/2,h/2-viewport.h/camera.scale*sy/2,viewport.w/camera.scale*sx,viewport.h/camera.scale*sy);
  }
  function frame(now){
    const dt=Math.min(.05,(now-lastFrame)/1000),t=now/1000;lastFrame=now;const smoothing=1-Math.exp(-dt*13);
    const renderTime=Number(snapshot.time||0)+Math.max(0,(now-lastSnapshotAt)/1000)-.1;
    for(const v of visuals.values()){const oldX=v.x,oldY=v.y,point=v.track.sample(renderTime);v.x=point.x;v.y=point.y;v.move+=Math.hypot(v.x-oldX,v.y-oldY)*.023;}
    const fps=fpsMeter.sample(now);if(fps&&playing){ui.fpsCounter.textContent=`${fps.fps} FPS`;ui.fpsCounter.title=`Średnia klatka: ${fps.ms.toFixed(1)} ms`;}
    if(me){const own=visuals.get(`p:${myId}`);if(own){camera.x+=(own.x-camera.x)*(1-Math.exp(-dt*8));camera.y+=(own.y-camera.y)*(1-Math.exp(-dt*8));}}
    else if(!playing){camera.x=690+Math.sin(t*.035)*65;camera.y=1040+Math.sin(t*.05)*65;}
    const halfW=viewport.w/camera.scale/2,halfH=viewport.h/camera.scale/2;
    camera.x=Math.max(Math.min(halfW,world.width/2),Math.min(world.width-Math.min(halfW,world.width/2),camera.x));camera.y=Math.max(Math.min(halfH,world.height/2),Math.min(world.height-Math.min(halfH,world.height/2),camera.y));
    ctx.setTransform(viewport.dpr,0,0,viewport.dpr,0,0);ctx.imageSmoothingEnabled=false;ctx.fillStyle="#668b48";ctx.fillRect(0,0,viewport.w,viewport.h);
    ctx.save();ctx.translate(Math.round(viewport.w/2),Math.round(viewport.h/2));ctx.scale(camera.scale,camera.scale);ctx.translate(-Math.round(camera.x),-Math.round(camera.y));
    drawGround();if(!(me?.floor)){drawWaterways(t);drawRiver(t);drawSafeZone();drawVillage(t);}
    const objects=[];
    for(const entry of nearbyDrawables()){
      const o=entry.data;
      if(entry.kind==='obstacle'){if(inView(o.x+o.w/2,o.y+o.h/2,Math.max(o.w,o.h)+80))objects.push({y:o.y+o.h,draw:()=>drawObstacle(o,entry.index)});}
      else if(entry.kind==='landmark'){if(inView(o.x,o.y))objects.push({y:o.y+20,draw:()=>drawLandmark(o,t)});}
      else if(entry.kind==='npc'){if(inView(o.x,o.y))objects.push({y:o.y+9,draw:()=>drawNPC(o,t)});}
      else if(entry.kind==='merchant'){if(inView(o.x,o.y))objects.push({y:o.y+12,draw:()=>drawMerchant(t)});}
    }
    for(const v of visuals.values())if(sameFloor(me,v.entity)&&inView(v.x,v.y))objects.push({y:v.y+(v.kind==='p'?21:10),draw:()=>v.kind==='p'?drawPlayer(v,t):drawEnemy(v,t)});
    for(const entry of nearbyDrawables()){
      const o=entry.data;
      if(entry.kind==='stair'&&inView(o.x,o.y))objects.push({y:o.y,draw:()=>drawStair(o)});
      if(entry.kind==='camp'&&inView(o.x,o.y,150))objects.push({y:o.y,draw:()=>drawCamp(o,t)});
    }
    objects.sort((a,b)=>a.y-b.y);for(const o of objects)o.draw();
    drawGoal();drawEffects(now);drawParticles(dt);for(const v of visuals.values())if(v.kind==="p"&&sameFloor(me,v.entity))drawSpeech(v,now);
    ctx.restore();drawMinimap();
    if(playing&&lastSnapshotAt&&now-lastSnapshotAt>5000)ui.connectionStatus.textContent="BRAK ODPOWIEDZI";else if(playing&&ui.connectionStatus.textContent!==" ONLINE")ui.connectionStatus.innerHTML="<i></i> ONLINE";
    requestAnimationFrame(frame);
  }
  document.addEventListener("visibilitychange",()=>fpsMeter.reset());
  requestAnimationFrame(frame);
})();
