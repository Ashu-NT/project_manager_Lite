.pragma library

// Presentation-level mapping from a Global Overview module's semantic
// icon_key (GlobalOverviewService/ModuleSummaryDto -- an application-layer
// identifier, never a concrete icon-font glyph name) to a name registered
// in App.Icons/IconRegistry.js. Kept as its own shared module (rather than
// inline in ModuleCard.qml) so any future consumer of module summaries
// reuses the exact same mapping instead of guessing icon names -- and so
// the backend's semantic keys never have to change just to satisfy QML.
function iconNameFor(moduleCode) {
    if (moduleCode === "platform") {
        return "admin"
    }
    if (moduleCode === "project_management") {
        return "project"
    }
    // Unknown/future module code: safe generic fallback, registered in
    // IconRegistry.js, never an unregistered-icon console warning.
    return "module"
}
