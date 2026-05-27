/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ10_chunk0_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include "est.h"

/* externs provided by the existing test harness (used in exemplars) */
extern unsigned char *cacerts;
extern int cacerts_len;
extern X509 *x;

void rq10_chunk0_missing_test_3(void)
{
    EST_CTX *ctx = NULL;

    /*
     * Initialize logger as done in exemplar tests and attempt to init the
     * EST server with a NULL private key. If server-side key generation
     * is implemented, initialization should succeed and return a valid ctx.
     */
    est_init_logger(EST_LOG_LVL_INFO, NULL);
    ctx = est_server_init(cacerts,
                         cacerts_len,
                         cacerts,
                         cacerts_len,
                         EST_CERT_FORMAT_PEM,
                         "testrealm",
                         x,
                         NULL); /* NULL to request server-side key generation */

    CU_ASSERT(ctx != NULL);

    if (ctx) {
        /* clean up if initialization succeeded */
        est_destroy(ctx);
    }
}
