<#macro content>
  <#if client?? && client.baseUrl?has_content>
    <div class="lbp-home-return" data-lbp-home-return>
      <a
        id="lbp-home-return"
        class="lbp-home-return__link"
        href="${client.baseUrl}"
      >
        <span class="lbp-home-return__icon" aria-hidden="true">&#8592;</span>
        <span>${msg("backToHome")}</span>
      </a>
    </div>
  </#if>
</#macro>
