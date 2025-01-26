FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

uniform vec2 resolution;
uniform float time;
uniform vec3 camera_pos;
uniform vec3 camera_dir;

const int NUM_LIGHTS = 5;
const int NUM_SPHERES = 27;

float fov = 45.0; // in degrees
float focal = tan(radians(fov) / 2.0);

struct Light {
    vec3 position;
    vec3 color;
};

uniform Light lights[NUM_LIGHTS];

struct Sphere {
    vec3 center;
    float radius;
    vec3 color;
    float reflectivity;
    float transparency;
    float ior; // Index of Refraction
    vec3 absorption;
};

struct Plane {
    vec3 point;
    vec3 normal;
    vec3 color;
    float reflectivity;
};

// Scene data (we'll fill these in initScene)
Sphere spheres[NUM_SPHERES];
Plane plane;
int maxBounces = 6;

// Basic ambient
vec3 ambient = vec3(0.05);


vec3 getSkyColor(vec3 rd) {
    float t = 0.5 * (rd.y + 1.0);
    return mix(vec3(0.5, 0.6, 0.8), vec3(0.0, 0.0, 0.3), t);
}

float sphereIntersection(vec3 ro, vec3 rd, Sphere sphere, out vec3 hitNormal) {
    vec3 oc = ro - sphere.center;
    float b = dot(oc, rd);
    float c = dot(oc, oc) - sphere.radius * sphere.radius;
    float h = b * b - c;
    if (h < 0.0) return -1.0;
    float t = -b - sqrt(h);
    if (t > 0.0) {
        vec3 hitPos = ro + rd * t;
        hitNormal = normalize(hitPos - sphere.center);
        return t;
    }
    return -1.0;
}

float planeIntersection(vec3 ro, vec3 rd, Plane pl, out vec3 hitNormal) {
    float denom = dot(rd, pl.normal);
    if (abs(denom) > 0.0001) {
        float t = dot(pl.point - ro, pl.normal) / denom;
        if (t > 0.0) {
            hitNormal = pl.normal;
            return t;
        }
    }
    return -1.0;
}


// This returns the fraction of light that is reflected at the interface.
// totalInternal is set to true if we have total internal reflection.
float fresnelSchlick(vec3 rd, vec3 n, float iorIn, float iorOut, out bool totalInternal) {
    totalInternal = false;
    float cosi = clamp(dot(rd, n), -1.0, 1.0);
    float etai = iorIn;
    float etat = iorOut;
    if (cosi > 0.0) {
        // we are inside the object looking out
        float temp = etai;
        etai = etat;
        etat = temp;
        n = -n;
        cosi = -cosi;
    }
    float etaRatio = etai / etat;
    float sint = etaRatio * sqrt(max(0.0, 1.0 - cosi * cosi));
    // Check total internal reflection
    if (sint >= 1.0) {
        totalInternal = true;
        return 1.0;
    } else {
        float cost = sqrt(max(0.0, 1.0 - sint * sint));
        cosi = abs(cosi);
        float Rs = (etat * cosi - etai * cost) / (etat * cosi + etai * cost);
        float Rp = (etai * cosi - etat * cost) / (etai * cosi + etat * cost);
        return (Rs * Rs + Rp * Rp) * 0.5;
    }
}

// This is a simple reflection function that does a single bounce.
vec3 computeReflectionColor(vec3 ro, vec3 rd) {
    // We do a simple trace: find the nearest object.
    float nearestT = -1.0;
    vec3 hitNormal = vec3(0.0);
    vec3 hitColor  = vec3(0.0);
    int hitObject  = -1; // 0= Sphere, 1= Plane
    int hitIndex   = -1;

    // Spheres
    for (int i = 0; i < NUM_SPHERES; i++) {
        vec3 n;
        float t = sphereIntersection(ro, rd, spheres[i], n);
        if (t > 0.0 && (t < nearestT || nearestT < 0.0)) {
            nearestT = t;
            hitNormal = n;
            hitColor = spheres[i].color;
            hitObject = 0;
            hitIndex = i;
        }
    }

    // Plane
    {
        vec3 n;
        float t = planeIntersection(ro, rd, plane, n);
        if (t > 0.0 && (t < nearestT || nearestT < 0.0)) {
            nearestT = t;
            hitNormal = n;
            hitColor = plane.color;
            hitObject = 1;
            hitIndex = -1;
        }
    }

    if (nearestT < 0.0) {
        // no intersection: return sky color
        return getSkyColor(rd);
    }

    // If we hit something, compute direct lighting (ambient + diffuse)
    vec3 hitPos = ro + rd * nearestT;

    // Simple direct lighting.
    vec3 totalDiffuse = vec3(0.0);
    for (int l = 0; l < NUM_LIGHTS; l++) {
        vec3 lightDir = normalize(lights[l].position - hitPos);
        // check shadow quickly
        float shadow = 1.0;
        // sphere shadow check
        for (int j = 0; j < NUM_SPHERES; j++) {
            vec3 tn;
            float ts = sphereIntersection(hitPos + hitNormal * 0.001, lightDir, spheres[j], tn);
            if (ts > 0.0) {
                shadow = 0.0;
                break;
            }
        }
        // plane shadow check
        {
            vec3 tn;
            float ts = planeIntersection(hitPos + hitNormal * 0.001, lightDir, plane, tn);
            if (ts > 0.0) {
                shadow = 0.0;
            }
        }
        float diff = max(dot(hitNormal, lightDir), 0.0) * shadow;
        totalDiffuse += diff * lights[l].color;
    }

    vec3 surfaceColor = (totalDiffuse * hitColor) + ambient;
    return surfaceColor;
}


// This function traces a single ray and returns the accumulated color.
vec3 traceRay(vec3 ro, vec3 rd) {
    vec3 colorAccum = vec3(0.0);
    vec3 attenuation = vec3(1.0);

    for (int bounce = 0; bounce < maxBounces; bounce++) {
        float nearestT = -1.0;
        vec3 hitNormal = vec3(0.0);
        vec3 hitColor = vec3(0.0);
        float hitReflect = 0.0;
        float hitTransp  = 0.0;
        float hitIOR     = 1.0;
        int hitObjectType = -1; // 0 = sphere, 1 = plane
        int hitIndex     = -1;

        // Intersect with spheres
        for (int i = 0; i < NUM_SPHERES; i++) {
            vec3 n;
            float t = sphereIntersection(ro, rd, spheres[i], n);
            if (t > 0.0 && (t < nearestT || nearestT < 0.0)) {
                nearestT = t;
                hitNormal = n;
                hitColor = spheres[i].color;
                hitReflect = spheres[i].reflectivity;
                hitTransp  = spheres[i].transparency;
                hitIOR     = spheres[i].ior;
                hitObjectType = 0;
                hitIndex   = i;
            }
        }
        // Intersect with plane
        {
            vec3 n;
            float t = planeIntersection(ro, rd, plane, n);
            if (t > 0.0 && (t < nearestT || nearestT < 0.0)) {
                nearestT = t;
                hitNormal = n;
                hitColor = plane.color;
                hitReflect = plane.reflectivity;
                hitTransp  = 0.0;
                hitIOR     = 1.0;
                hitObjectType = 1;
                hitIndex   = -1;
            }
        }

        // If we didn't hit anything, add sky color & end
        if (nearestT < 0.0) {
            vec3 sky = getSkyColor(rd);
            colorAccum += attenuation * sky;
            break;
        }

        // We hit something
        vec3 hitPos = ro + rd * nearestT;

        // Direct lighting at the hit
        {
            vec3 totalDiffuse = vec3(0.0);
            for (int l = 0; l < NUM_LIGHTS; l++) {
                vec3 lightDir = normalize(lights[l].position - hitPos);
                float shadow = 1.0;
                // check shadow
                for (int j = 0; j < NUM_SPHERES; j++) {
                    vec3 tn;
                    float tShadow = sphereIntersection(hitPos + hitNormal * 0.001, lightDir, spheres[j], tn);
                    if (tShadow > 0.0) {
                        shadow = 0.0;
                        break;
                    }
                }
                {
                    vec3 tn;
                    float tShadowPlane = planeIntersection(hitPos + hitNormal * 0.001, lightDir, plane, tn);
                    if (tShadowPlane > 0.0) {
                        shadow = 0.0;
                    }
                }
                float diff = max(dot(hitNormal, lightDir), 0.0) * shadow;
                totalDiffuse += diff * lights[l].color;
            }
            vec3 lighting = totalDiffuse * hitColor + ambient;
            // add this surface's direct shading to the accumulation
            colorAccum += attenuation * lighting;
        }

        // Reflection / Refraction logic
        bool totalInternal = false;
        float kr = fresnelSchlick(rd, hitNormal, 1.0, hitIOR, totalInternal);

        // If object is transparent
        if (hitTransp > 0.0) {
            // PARTIAL REFLECTION: do a quick reflection sample.
            if (!totalInternal && kr > 0.0) {
                vec3 reflectDir = reflect(rd, hitNormal);
                vec3 reflectOrigin = hitPos + reflectDir * 0.001;
                vec3 reflectionColor = computeReflectionColor(reflectOrigin, reflectDir);

                // Weighted add
                colorAccum += attenuation * reflectionColor * kr * hitReflect;
            } else if (totalInternal) {
                // If total internal reflection, reflection is effectively 100%
                kr = 1.0;
            }

            // Now continue the main path as refraction if not TIR
            if (kr < 1.0) {
                // Beer–Lambert
                float distInMedium = nearestT; // approximate
                vec3 absorb = vec3(0.0);
                if (hitObjectType == 0 && hitIndex >= 0) {
                    absorb = spheres[hitIndex].absorption;
                }
                attenuation *= exp(-absorb * distInMedium);

                // scale attenuation by (1-kr)*transparency
                attenuation *= (1.0 - kr) * hitTransp;

                // Refract
                vec3 n = hitNormal;
                float cosi = dot(rd, n);
                if (cosi > 0.0) n = -n;

                float eta = (cosi > 0.0) ? (hitIOR / 1.0) : (1.0 / hitIOR);
                vec3 refractDir = refract(rd, n, eta);

                ro = hitPos + refractDir * 0.001;
                rd = refractDir;
            } else {
                // total internal reflection or near total reflection
                // reflect the main ray
                attenuation *= hitReflect;
                vec3 reflectDir = reflect(rd, hitNormal);
                ro = hitPos + reflectDir * 0.001;
                rd = reflectDir;
            }
        }
        else if (hitReflect > 0.0) {
            // Opaque + reflective
            attenuation *= hitReflect;
            vec3 reflectDir = reflect(rd, hitNormal);
            ro = hitPos + reflectDir * 0.001;
            rd = reflectDir;
        }
        else {
            // Opaque and not reflective => no further bounces, we are done
            break;
        }
    } // end bounce loop

    return colorAccum;
}


void initScene() {
    // Spheres
    spheres[0] = Sphere(
        vec3(-1.5, 0.0, 5.0), // center
        1.0,                  // radius
        vec3(1.0, 0.0, 0.0),  // color
        0.2,                  // reflectivity
        0.0,                  // transparency
        1.0,                  // ior
        vec3(0.0)            // absorption
    );
    spheres[1] = Sphere(
        vec3(1.5, 0.0, 6.0), // center
        1.0,                // radius
        vec3(0.0, 0.0, 1.0),  // color
        0.8,  // reflectivity
        0.0,  // transparency
        1.0,  // ior
        vec3(0.02) // absorption
    );
    spheres[2] = Sphere(
        vec3(0.0, -0.5, 3.0), // center
        0.5,                 // radius
        vec3(0.9, 0.9, 0.9), // color
        0.2,  // reflectivity
        0.95, // transparency
        0.87,  // ior
        vec3(0.0) // absorption
    );
    spheres[3] = Sphere(
        vec3(2.0, -0.3, 3.0),
        0.7,
        vec3(0.7, 0.6, 0.5),
        0.1,  // reflectivity
        0.95, // transparency
        0.87,  // ior
        vec3(0.0)
    );


    // Random spheres on a circle
    float ringRadius = 3.5;
    int ringCount = 23;
    for(int i = 0; i < ringCount; i++){
        int sIndex = 4 + i;

        // angle around circle
        float angle = 2.0 * 3.14159 * float(i) / float(ringCount); 

        // position on circle
        float xPos = ringRadius * cos(angle);
        float zPos = 3.5 + ringRadius * sin(angle);

        // slightly vary radius between 0.15 and 0.20
        float rad = (i % 2 == 0) ? 0.20 : 0.15;
        float yPos = -1.0 + rad;  // sits on plane

        vec3 col = vec3(
            0.3 + 0.7 * fract(sin(float(i)*12.345)*9876.543), // randomish red
            0.3 + 0.7 * fract(sin(float(i)*3.217)*5432.123),  // randomish green
            0.3 + 0.7 * fract(sin(float(i)*5.789)*6543.234)   // randomish blue
        );

        // reflectivity or transparency also randomish
        float refl = 0.1 + 0.4*fract(sin(float(i)*1.111)*777.0);   // between 0.1..0.5
        float transp = 0.2 * fract(sin(float(i)*2.222)*123.0);     // between 0..0.2
        float iorVal = 1.0 + 0.5*fract(sin(float(i)*4.444)*987.0); // between 1..1.5

        spheres[sIndex] = Sphere(
            vec3(xPos, yPos, zPos),
            rad,
            col,
            refl,
            transp,
            iorVal,
            vec3(0.0) // no absorption for now
        );
    }





    // Plane
    plane = Plane(
        vec3(0.0, -1.0, 0.0), // point
        vec3(0.0, 1.0, 0.0),  // normal
        vec3(0.32, 0.18, 0.26), // color
        0.4 // reflectivity
    );
}

void main(){
    initScene();

    // Compute normalized screen coords
    vec2 uv = (gl_FragCoord.xy / resolution.xy) * 2.0 - 1.0;
    uv.x *= resolution.x / resolution.y;

    // Build initial ray
    vec3 ro = camera_pos;

    // Simple pinhole camera approach with adjustable FOV
    uv *= focal;
    vec3 rd = normalize(camera_dir + vec3(uv, 0.0));

    // Trace!
    vec3 finalColor = traceRay(ro, rd);
    FragColor = vec4(finalColor, 1.0);
}
"""