/* Authored pictograms matching the actual destination of each HUD control. */
(function(root){'use strict';
 const icons={progressionButton:'character',journalButton:'journal',inventoryButton:'inventory',partyButton:'party',mapButton:'minimap',topAtlasButton:'atlas',helpButton:'help',logoutButton:'logout',fullscreenButton:'fullscreen',installAppButton:'install',mobileFullscreenButton:'fullscreen'};
 function apply(doc){for(const[id,key]of Object.entries(icons)){const b=doc.getElementById(id);if(!b)continue;const img=doc.createElement('img');img.className='hud-icon';img.alt='';img.src='assets/ui/'+key+'.svg';b.replaceChildren(img);}}
 root.BractwoHUDIcons={apply,icons};if(typeof module!=='undefined')module.exports={apply,icons};
})(globalThis);
