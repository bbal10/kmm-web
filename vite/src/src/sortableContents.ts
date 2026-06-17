import Sortable from 'sortablejs';

// Orphaned helper. Guarded so it doesn't crash on pages without #modules.
const modules = document.getElementById("modules");

export const sortable = modules ? Sortable.create(modules as HTMLElement, {}) : null;