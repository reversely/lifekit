<script lang="ts">
  import type { Database } from '../core/db';
  import { shelves } from '../core/queries';
  export let db: Database;
  import { volumes } from '../core/queries';
  const list = shelves(db);
  const total = volumes(db).length;
</script>

<div class="dir">
  <div class="screen">
    <div class="top"><h1>Library</h1></div>
    <div class="digest">
      <h2>Since you were last online</h2>
      <p>{total} volumes added.</p>
    </div>
    <div class="label">CONTENTS</div>
    {#each list as s}
      <a class="row" href={`#/section/${s.id}`}>
        <div class="n">{s.order}</div>
        <div>
          <div class="t">{s.title}</div>
          <div class="s">{s.scopeLine}</div>
          {#if s.count}<div class="c some">{s.count} volumes</div>{:else}<div class="c">none yet</div>{/if}
        </div>
        <div></div>
      </a>
    {/each}
  </div>
</div>
