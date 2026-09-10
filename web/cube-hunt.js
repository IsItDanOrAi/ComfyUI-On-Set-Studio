/* ============================================================================
   cube-hunt.js  --  On-Set Studio capture-leak diagnostic  (console paste)
   ----------------------------------------------------------------------------
   PURPOSE
     Answers "what is actually still visible when MakeImages renders a pass?"
     without a build, a version bump, or a source edit.

   HOW IT WORKS
     Replays the exact three hides MakeImages performs -- hideHelpersForCapture
     on every body, the renderOrder>=999 on-top sweep, the v219 Actor Mark
     sweep, plus frameHelper -- then walks the scene and lists every drawable
     that SURVIVED, with its world bounding box, world centre, parent chain,
     and vertex count. Everything is restored before it returns.

   READING THE OUTPUT
     - vcount 24  ->  almost certainly a THREE.BoxGeometry (24 verts, 4/face).
       The BOX? column flags these. Three of them at head height / foot height
       is the bug, named.
     - cY is world height. Y Bot is ~170 units tall, so head ~150-170,
       feet ~0-15.
     - "chain" is the parent path back to the scene, so a hit tells you which
       system owns it, not just that something leaked.

   USAGE
     Paste into the editor tab's devtools console with a character loaded and
     the scene in the state that produces the cubes. Read-only -- restores all
     visibility on exit.
============================================================================ */
;(() => {
    const e = window.bodyEditor
    if (!e) {
        console.error('[cube-hunt] window.bodyEditor missing -- wrong tab?')
        return
    }

    // ---- 1. replay MakeImages' hides -------------------------------------
    const restores = []
    try {
        if (e.mixamoBody && e.mixamoBody.hideHelpersForCapture)
            restores.push(e.mixamoBody.hideHelpersForCapture())
        for (const c of e.extraChars || [])
            if (c.body && c.body.hideHelpersForCapture)
                restores.push(c.body.hideHelpersForCapture())
    } catch (err) {
        console.warn('[cube-hunt] hideHelpersForCapture threw', err)
    }

    const hardHidden = []
    const hide = (o) => {
        if (o && o.visible) {
            o.visible = false
            hardHidden.push(o)
        }
    }

    e.scene.traverse((o) => {
        const drawable = o.isMesh || o.isLine || o.isPoints
        if (drawable && o.visible && o.renderOrder >= 999) hide(o)
    })

    try {
        for (const [, list] of e.actorMarks || new Map())
            for (const m of list) hide(m && m.obj)
    } catch (err) {
        console.warn('[cube-hunt] actorMarks sweep threw', err)
    }
    hide(e.frameHelper)

    // ---- 2. walk what survived -------------------------------------------
    // Vector3 without a THREE global: clone one that already exists.
    const v = e.scene.position.clone()

    const visibleUpChain = (o) => {
        let p = o
        while (p) {
            if (!p.visible) return false
            p = p.parent
        }
        return true
    }

    const chainOf = (o) => {
        const parts = []
        let p = o
        while (p && p !== e.scene) {
            parts.push(p.name || p.type)
            p = p.parent
        }
        return parts.join(' < ')
    }

    const rows = []
    e.scene.traverse((o) => {
        if (!(o.isMesh || o.isLine || o.isPoints)) return
        if (!visibleUpChain(o)) return
        const g = o.geometry
        const pos = g && g.attributes && g.attributes.position
        if (!pos || !pos.count) return

        o.updateWorldMatrix(true, false)
        let mnx = Infinity, mny = Infinity, mnz = Infinity
        let mxx = -Infinity, mxy = -Infinity, mxz = -Infinity
        // Sample large meshes; exact for anything helper-sized.
        const step = pos.count > 20000 ? Math.ceil(pos.count / 20000) : 1
        for (let i = 0; i < pos.count; i += step) {
            v.set(pos.getX(i), pos.getY(i), pos.getZ(i)).applyMatrix4(
                o.matrixWorld
            )
            if (v.x < mnx) mnx = v.x
            if (v.y < mny) mny = v.y
            if (v.z < mnz) mnz = v.z
            if (v.x > mxx) mxx = v.x
            if (v.y > mxy) mxy = v.y
            if (v.z > mxz) mxz = v.z
        }
        const r = (n) => Math.round(n * 10) / 10
        const mat = Array.isArray(o.material) ? o.material[0] : o.material

        rows.push({
            name: o.name || '(unnamed)',
            'BOX?': pos.count === 24 ? '<<< BOX' : '',
            vcount: pos.count,
            geo: (g && g.type) || '?',
            sx: r(mxx - mnx),
            sy: r(mxy - mny),
            sz: r(mxz - mnz),
            cX: r((mnx + mxx) / 2),
            cY: r((mny + mxy) / 2),
            cZ: r((mnz + mxz) / 2),
            ro: o.renderOrder,
            depthTest: mat ? mat.depthTest : '?',
            mat: mat ? mat.type : '?',
            color:
                mat && mat.color ? '#' + mat.color.getHexString() : '',
            chain: chainOf(o),
        })
    })

    // Smallest first -- helper glyphs sort to the top, body meshes to the end.
    rows.sort((a, b) => a.sx * a.sy * a.sz - b.sx * b.sy * b.sz)

    console.log(
        `[cube-hunt] ${rows.length} drawables survive the capture hides ` +
            `(${rows.filter((x) => x['BOX?']).length} look like BoxGeometry)`
    )
    console.table(rows)

    // ---- 3. restore -------------------------------------------------------
    restores.forEach((r) => typeof r === 'function' && r())
    hardHidden.forEach((o) => (o.visible = true))
    console.log('[cube-hunt] visibility restored')

    return rows
})()
