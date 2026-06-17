import "@fortawesome/fontawesome-free";
import Sortable from 'sortablejs';
import NotifyX from "notifyx";
import "notifyx/style.css"

// Only run Sortable on pages that have the containers
const modules = document.getElementById("modules");
const contents = document.getElementById("module-contents");

if (modules) {
  Sortable.create(modules as HTMLElement, {
    onUpdate: () => {
      const updateModuleOrderUrl = (modules as HTMLElement).dataset.updateModuleOrderUrl || 
                                   (contents as HTMLElement | null)?.dataset.updateModuleOrderUrl || "";
      const modulesListArr = Array.from(modules.children);
      const moduleList = modulesListArr.reduce((acc, arr, index) => {
        const el = arr as HTMLElement;
        if (el.dataset?.id) {
          acc[el.dataset.id] = index + 1;
        }
        return acc;
      }, {} as Record<string, number>);
      
      if (updateModuleOrderUrl) {
        const options: RequestInit = {
          method: "POST",
          mode: "same-origin",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(moduleList),
        };
        
        fetch(updateModuleOrderUrl, options)
          .then(() => NotifyX.success("Urutan modul berhasil diperbarui"))
          .catch(() => NotifyX.error("Gagal memperbarui urutan modul"));
      }
    },
  });
}

if (contents) {
  Sortable.create(contents as HTMLElement, {
    onUpdate: () => {
      const updateContentOrderUrl = (contents as HTMLElement).dataset.updateContentOrderUrl || "";
      const contentsListArr = Array.from(contents.children);
      const contentList = contentsListArr.reduce((acc, arr, index) => {
        const el = arr as HTMLElement;
        if (el.dataset?.id) {
          acc[el.dataset.id] = index + 1;
        }
        return acc;
      }, {} as Record<string, number>);
      
      if (updateContentOrderUrl) {
        const options: RequestInit = {
          method: "POST",
          mode: "same-origin",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(contentList),
        };
        
        fetch(updateContentOrderUrl, options)
          .then(() => NotifyX.success("Urutan konten berhasil diperbarui"))
          .catch(() => NotifyX.error("Gagal memperbarui urutan konten"));
      }
    },
  });
}

// Content deleted event listener
document.body.addEventListener("contentDeleted", () => {
  NotifyX.success("Konten berhasil dihapus");
});

// Accessibility: Add focus styles for keyboard navigation
function initializeAccessibility() {
  const focusableElements = document.querySelectorAll(
    'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  focusableElements.forEach(el => {
    el.addEventListener('keydown', (e: any) => {
      if (e.key === 'Tab') {
        el.classList.add('focus-visible');
      }
    });
    
    el.addEventListener('blur', () => {
      el.classList.remove('focus-visible');
    });
  });
}

// Run on DOM load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeAccessibility);
} else {
  initializeAccessibility();
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (this: any, e: any) {
    e.preventDefault();
    const href = this.getAttribute('href');
    if (href) {
      const target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    }
  });
});
