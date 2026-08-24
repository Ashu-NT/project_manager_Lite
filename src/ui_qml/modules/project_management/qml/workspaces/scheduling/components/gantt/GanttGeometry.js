.pragma library

function dayStartX(dayOrdinal, axisStartDay, pixelsPerDay) {
    return (Number(dayOrdinal) - Number(axisStartDay)) * Number(pixelsPerDay)
}

function dayCenterX(dayOrdinal, axisStartDay, pixelsPerDay) {
    return dayStartX(dayOrdinal, axisStartDay, pixelsPerDay)
        + Number(pixelsPerDay) / 2
}

function inclusiveWidth(startDay, finishDay, pixelsPerDay) {
    return Math.max(
        0,
        (Number(finishDay) - Number(startDay) + 1) * Number(pixelsPerDay)
    )
}

function taskWidth(startDay, finishDay, pixelsPerDay) {
    return Math.max(12, inclusiveWidth(startDay, finishDay, pixelsPerDay))
}

function taskFinishX(startDay, finishDay, axisStartDay, pixelsPerDay) {
    return dayStartX(startDay, axisStartDay, pixelsPerDay)
        + taskWidth(startDay, finishDay, pixelsPerDay)
}

function milestoneSize() {
    return 14
}

function milestoneStartX(dayOrdinal, axisStartDay, pixelsPerDay) {
    return dayCenterX(dayOrdinal, axisStartDay, pixelsPerDay) - milestoneSize() / 2
}

function milestoneFinishX(dayOrdinal, axisStartDay, pixelsPerDay) {
    return dayCenterX(dayOrdinal, axisStartDay, pixelsPerDay) + milestoneSize() / 2
}
